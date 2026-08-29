# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "etax.service.mixin"]

    _etax_sign_api_code = "FRAPPE_ETAX_SIGN"

    is_credit_payment_entry = fields.Boolean(
        string="Use Credit Note on Payment",
        default=False,
        help="This is used to indicate this document \
            will cancel etax payment on INET (Case Etax)",
    )
    etax_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Etax Payment",
        help="If 'Use Credit Note on Payment' is selected, \
            Select payment for retrieve original data.",
    )
    replaced_entry_id = fields.Many2one(
        comodel_name="account.move",
        string="Replaced Document",
        readonly=True,
        copy=False,
        help="Currently this field only support invoice and not payment",
    )
    is_etax_configured = fields.Boolean(
        related="company_id.is_etax_configured",
    )
    enable_etax = fields.Boolean(
        compute="_compute_enable_etax",
        store=True,
    )

    @api.depends("move_type", "etax_status", "state", "is_etax_configured")
    def _compute_enable_etax(self):
        for rec in self:
            rec.enable_etax = (
                rec.move_type in ("out_invoice", "out_refund", "out_invoice_debit")
                and rec.etax_status not in ("success", "processing")
                and rec.state == "posted"
                and rec.company_id.is_etax_configured
            )

    @api.onchange("is_credit_payment_entry", "create_purpose")
    def _onchange_ref(self):
        if self.is_credit_payment_entry:
            self.ref = self.create_purpose

    def _get_additional_amount(self):
        """
        In case of credit note, debit note or replacement tax invoice
        Get original untax amount for
            f36_original_total_amount = original_amount_untaxed
            f40_adjusted_information_amount = diff_amount_untaxed
            f38_line_total_amount = corrected_amount_untaxed
        """
        original_amount_untaxed = corrected_amount_untaxed = diff_amount_untaxed = False
        if self.debit_origin_id:
            original_amount_untaxed = self.debit_origin_id.amount_untaxed
            diff_amount_untaxed = self.amount_untaxed
            corrected_amount_untaxed = original_amount_untaxed + diff_amount_untaxed
        if self.reversed_entry_id:
            original_amount_untaxed = self.reversed_entry_id.amount_untaxed
            diff_amount_untaxed = self.amount_untaxed
            corrected_amount_untaxed = original_amount_untaxed - diff_amount_untaxed
        if self.replaced_entry_id:
            original_amount_untaxed = False
            diff_amount_untaxed = False
            corrected_amount_untaxed = self.amount_untaxed
        return (original_amount_untaxed, diff_amount_untaxed, corrected_amount_untaxed)

    @api.depends("restrict_mode_hash_table", "state")
    def _compute_show_reset_to_draft_button(self):
        res = super()._compute_show_reset_to_draft_button()
        # If etax signed, user can't just reset to draft.
        # User need to create replacement invoice, do the update and submit eTax again.
        for move in self.filtered(lambda m: m.etax_status == "success"):
            move.show_reset_to_draft_button = False
        return res

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
        """Create replacement document and cancel the old one"""
        self.ensure_one()
        if not (self.state == "posted" and self.etax_status == "success"):
            raise ValidationError(
                self.env._("Only posted etax invoice can have a substitution")
            )

        ctx = {
            "include_business_fields": True,
            "force_copy_stock_moves": True,
        }
        res = self.with_context(**ctx).copy_data()[0]

        # Preserve important fields manually
        res.update(
            {
                "posted_before": self.posted_before,
                "payment_reference": self.payment_reference,
                "invoice_date": self.invoice_date,
                "invoice_date_due": self.invoice_date_due,
                "etax_doctype_id": self.etax_doctype_id.id,
                "replaced_entry_id": self.id,
            }
        )

        move = self.create(res)
        self.button_draft()
        self.button_cancel()
        return move

    def _hook_update_data(self, code_api, result):
        res = super()._hook_update_data(code_api, result)
        if code_api == self._etax_sign_api_code and self.etax_status == "success":
            if self.replaced_entry_id:
                self.replaced_entry_id.etax_status = "replace"
        return res

    def _prepare_context_for_wizard(self, **kwargs):
        move_type = list(set(self.mapped("move_type")))
        if len(move_type) > 1:
            raise UserError(self.env._("Please select only one type"))
        has_debit = self.filtered("debit_origin_id")
        if has_debit and has_debit != self:
            raise UserError(self.env._("Please select only one type"))
        effective_move_type = "out_invoice_debit" if has_debit else move_type[0]
        kwargs.update(
            {
                "default_move_type": effective_move_type,
                # NOTE: Ensure active_ids is current id,
                # because when click e-Tax Invoice from Invoice > Invoice (replacement),
                # active_ids will be original invoice id
                "active_model": "account.move",
                "active_ids": self.ids,
                "active_id": self.id,
            }
        )
        if self.replaced_entry_id and self.etax_doctype_id:
            kwargs.update(
                {
                    "default_etax_doctype_id": self.etax_doctype_id.id,
                    "default_etax_doctype_locked": True,
                }
            )
        return super()._prepare_context_for_wizard(**kwargs)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    skip_etax = fields.Boolean(default=False)
