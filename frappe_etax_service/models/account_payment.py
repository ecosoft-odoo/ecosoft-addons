# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "etax.service.mixin"]

    _etax_sign_api_code = "FRAPPE_ETAX_PAYMENT_SIGN"
    _etax_replace_api_code = "FRAPPE_ETAX_PAYMENT_REPLACE"

    has_create_replacement = fields.Boolean(
        copy=False,
        default=False,
    )
    replacement_origin_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Original Payment",
        readonly=True,
        copy=False,
        help="Original payment for which this replacement was created.",
    )
    replacement_payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="replacement_origin_payment_id",
        string="Replacement Payments",
        readonly=True,
        help="Replacement payments created from this payment.",
    )
    is_etax_configured = fields.Boolean(
        related="company_id.is_etax_configured",
    )
    enable_etax = fields.Boolean(
        compute="_compute_enable_etax",
        store=True,
    )

    @api.depends("etax_status", "state", "is_etax_configured")
    def _compute_enable_etax(self):
        for rec in self:
            rec.enable_etax = (
                rec.etax_status not in ("success", "processing")
                and rec.state == "paid"
                and rec.company_id.is_etax_configured
            )

    def _hook_update_data(self, code_api, result):
        res = super()._hook_update_data(code_api, result)
        if code_api == self._etax_sign_api_code and self.etax_status == "success":
            if self.replacement_origin_payment_id:
                self.replacement_origin_payment_id.etax_status = "replace"
        return res

    def action_draft(self):
        if (
            self.filtered(
                lambda pay: pay.etax_status in ("success", "processing", "to_process")
            )
            and not self.has_create_replacement
            and not self.env.context.get("force_reset", False)
        ):
            raise ValidationError(
                self.env._(
                    "Cannot reset to draft, eTax submission already started "
                    "or succeeded.\n"
                    "You should do the refund process instead."
                )
            )
        return super().action_draft()

    def _validate_replacement_invoices(self):
        valid_account_types = ("asset_receivable", "liability_payable")
        for payment in self.filtered("replacement_origin_payment_id"):
            invoices = payment.invoice_ids
            if len(invoices) > 1:
                raise ValidationError(
                    self.env._("Multiple invoices are not allowed for a replacement")
                )
            if invoices.filtered(lambda invoice: invoice.state != "posted"):
                raise ValidationError(
                    self.env._(
                        "The invoice to reconcile must be posted before confirming "
                        "the replacement payment."
                    )
                )
            if invoices and invoices.company_id != payment.company_id:
                raise ValidationError(
                    self.env._(
                        "The replacement payment and invoice to reconcile must belong "
                        "to the same company."
                    )
                )
            if (
                invoices
                and invoices.commercial_partner_id
                != payment.partner_id.commercial_partner_id
            ):
                raise ValidationError(
                    self.env._(
                        "The replacement payment and invoice to reconcile must belong "
                        "to the same customer or vendor. Correct the source invoice "
                        "before confirming a replacement for another party."
                    )
                )
            if invoices and not invoices.line_ids.filtered(
                lambda line: line.account_id.reconcile
                and line.account_id.account_type in valid_account_types
                and not line.reconciled
            ):
                raise ValidationError(
                    self.env._(
                        "The invoice to reconcile has no outstanding receivable or "
                        "payable amount."
                    )
                )

    def _reconcile_replacement_invoices(self):
        # OCA account_payment_state_keep_draft uses the same invoice_ids link.
        # Filtering reconciled lines keeps both action_post hooks idempotent.
        valid_account_types = ("asset_receivable", "liability_payable")
        for payment in self.filtered(
            lambda pay: pay.replacement_origin_payment_id and pay.invoice_ids
        ):
            if not payment.move_id:
                raise ValidationError(
                    self.env._(
                        "The replacement payment must create a journal entry before "
                        "it can be reconciled."
                    )
                )
            invoice_lines = payment.invoice_ids.line_ids.filtered(
                lambda line: line.account_id.reconcile
                and line.account_id.account_type in valid_account_types
                and not line.reconciled
            )
            payment_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.reconcile
                and line.account_id.account_type in valid_account_types
                and not line.reconciled
            )
            common_accounts = invoice_lines.account_id & payment_lines.account_id
            if invoice_lines and payment_lines and not common_accounts:
                raise ValidationError(
                    self.env._(
                        "The replacement payment and invoice must use the same "
                        "receivable or payable account."
                    )
                )
            for account in common_accounts:
                lines = invoice_lines.filtered(
                    lambda line, account=account: line.account_id == account
                ) | payment_lines.filtered(
                    lambda line, account=account: line.account_id == account
                )
                lines.reconcile()

    def action_post(self):
        self._validate_replacement_invoices()
        res = super().action_post()
        self._reconcile_replacement_invoices()
        return res

    def _pre_etax_validate(self):
        res = super()._pre_etax_validate()
        missing_lines = self.filtered(
            lambda payment: not payment.tax_invoice_ids
            and not payment.reconciled_invoice_ids.invoice_line_ids
        )
        if missing_lines:
            names = ", ".join(missing_lines.mapped("display_name"))
            raise ValidationError(
                self.env._(
                    "%s: no e-Tax line items found. Add Tax Invoice information "
                    "or reconcile the payment with a Customer Invoice before "
                    "signing e-Tax."
                )
                % names
            )
        return res

    def _prepare_context_for_wizard(self, **kwargs):
        move_type = list(set(self.move_id.mapped("move_type")))
        if len(move_type) > 1:
            raise UserError(self.env._("Please select only one type"))
        kwargs.update(
            {
                "default_move_type": move_type[0],
                # NOTE: Ensure active_model is payment,
                # because when click e-Tax Invoice from Invoice > Payment,
                # active_model will send with account.move
                "active_model": "account.payment",
                "active_ids": self.ids,
                "active_id": self.id,
            }
        )
        if self.replacement_origin_payment_id and self.etax_doctype_id:
            kwargs.update(
                {
                    "default_etax_doctype_id": self.etax_doctype_id.id,
                    "default_etax_doctype_locked": True,
                }
            )
        return super()._prepare_context_for_wizard(**kwargs)

    def action_open_replacement_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Create Replacement"),
            "res_model": "etax.replacement.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": self._name,
                "default_etax_doctype_code": self.etax_doctype_code,
                "default_origin_ref": f"{self._name},{self.id}",
            },
        }

    def create_replacement_etax(self):
        """Create replacement receipt eTax"""
        self.ensure_one()
        if not (self.state == "paid" and self.etax_status == "success"):
            raise ValidationError(
                self.env._("Only posted etax payment can have a substitution")
            )
        if len(self.reconciled_invoice_ids) > 1:
            raise ValidationError(
                self.env._("Multiple reconciled invoices not allowed")
            )
        invoices = self.reconciled_invoice_ids
        res = self.with_context(include_business_fields=True).copy_data()[0]

        # Preserve important fields manually
        res.update(
            {
                "date": self.date,
                "etax_doctype_id": self.etax_doctype_id.id,
                "replacement_origin_payment_id": self.id,
                "invoice_ids": [Command.set(invoices.ids)],
            }
        )

        payment = self.create(res)
        self.has_create_replacement = True
        self.action_cancel()
        return payment
