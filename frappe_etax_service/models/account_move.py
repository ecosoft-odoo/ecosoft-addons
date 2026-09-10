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
    etax_refund_reason_id = fields.Many2one(
        comodel_name="etax.purpose.code",
        string="eTax Refund Reason",
        compute="_compute_etax_refund_reason_id",
        inverse="_inverse_etax_refund_reason_id",
        domain="[('etax_doctype_code_ids.code', '=', etax_adjustment_doctype_code)]",
        help="Optional for accounting. "
        "Required before signing a credit/debit note as e-Tax.",
    )
    etax_adjustment_doctype_code = fields.Char(
        compute="_compute_etax_adjustment_doctype_code",
    )

    @api.depends("move_type", "debit_origin_id")
    def _compute_etax_adjustment_doctype_code(self):
        for rec in self:
            rec.etax_adjustment_doctype_code = (
                "81"
                if rec.move_type == "out_refund"
                else "80"
                if rec.move_type == "out_invoice_debit"
                or (rec.move_type == "out_invoice" and rec.debit_origin_id)
                else False
            )

    @api.depends("create_purpose_code", "etax_adjustment_doctype_code")
    def _compute_etax_refund_reason_id(self):
        for rec in self:
            rec.etax_refund_reason_id = self.env["etax.purpose.code"].search(
                [
                    ("code", "=", rec.create_purpose_code),
                    (
                        "etax_doctype_code_ids.code",
                        "=",
                        rec.etax_adjustment_doctype_code,
                    ),
                ],
                limit=1,
            )

    def _inverse_etax_refund_reason_id(self):
        for rec in self:
            if rec.state != "draft" or rec.etax_status in (
                "success",
                "processing",
                "replace",
            ):
                raise ValidationError(
                    self.env._(
                        "The eTax Refund Reason can only be changed "
                        "in draft before signing."
                    )
                )
            purpose = rec.etax_refund_reason_id
            if purpose and rec.etax_adjustment_doctype_code not in (
                purpose.etax_doctype_code_ids.mapped("code")
            ):
                raise ValidationError(
                    self.env._("Select an eTax reason for this credit/debit note.")
                )
            rec.create_purpose_code = purpose.code

    @api.onchange("etax_refund_reason_id")
    def _onchange_etax_refund_reason_id(self):
        self.create_purpose = self.etax_refund_reason_id.reason

    def _has_etax_refund_reason(self):
        self.ensure_one()
        return bool(
            (self.create_purpose_code or "").strip()
            and (self.create_purpose or "").strip()
        )

    def _check_etax_refund_reason(self):
        for rec in self.filtered("etax_adjustment_doctype_code"):
            if not rec._has_etax_refund_reason():
                raise ValidationError(
                    self.env._(
                        "%s: To send this credit/debit note as e-Tax, "
                        "reset it to draft and select an eTax Refund Reason "
                        "and enter its description "
                        "in the e-Tax Info tab."
                    )
                    % rec.display_name
                )

    def _pre_etax_validate(self):
        self._check_etax_refund_reason()
        return super()._pre_etax_validate()

    def action_call_api(self, code_api):
        if code_api == self._etax_sign_api_code:
            self._check_etax_refund_reason()
        return super().action_call_api(code_api)

    @api.depends(
        "move_type",
        "etax_status",
        "state",
        "is_etax_configured",
        "create_purpose_code",
        "create_purpose",
        "etax_adjustment_doctype_code",
    )
    def _compute_enable_etax(self):
        for rec in self:
            rec.enable_etax = (
                rec.move_type in ("out_invoice", "out_refund", "out_invoice_debit")
                and rec.etax_status not in ("success", "processing")
                and rec.state == "posted"
                and rec.company_id.is_etax_configured
                and (
                    not rec.etax_adjustment_doctype_code
                    or rec._has_etax_refund_reason()
                )
            )

    @api.onchange("is_credit_payment_entry", "create_purpose")
    def _onchange_ref(self):
        if self.is_credit_payment_entry:
            self.ref = self.create_purpose

    def _get_etax_document_data(self):
        """Prepare invoice references, adjustments and signed line amounts."""
        data = super()._get_etax_document_data()
        original, adjustment, _corrected = self._get_additional_amount()
        data.update(
            {
                "document_issue_dtm": self.invoice_date
                and self.invoice_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "ref_document_id": self.debit_origin_id.name
                or self.reversed_entry_id.name
                or self.replaced_entry_id.name,
                "ref_document_issue_dtm": (
                    self.debit_origin_id.invoice_date
                    and self.debit_origin_id.invoice_date.strftime("%Y-%m-%dT%H:%M:%S")
                )
                or (
                    self.reversed_entry_id.invoice_date
                    and self.reversed_entry_id.invoice_date.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                )
                or (
                    self.replaced_entry_id.invoice_date
                    and self.replaced_entry_id.invoice_date.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                ),
                "ref_document_type_code": self.debit_origin_id.etax_doctype_code
                or self.reversed_entry_id.etax_doctype_code
                or self.replaced_entry_id.etax_doctype_code,
                "buyer_ref_document": self.payment_reference,
                "original_amount_untaxed": original,
                "final_amount_untaxed": self._get_etax_final_amount_untaxed(),
                "adjust_amount_untaxed": adjustment,
                "line_item_information": self._get_etax_line_item_information(),
            }
        )
        return data

    def _get_etax_invoice_lines(self):
        """Return product lines included in the invoice e-Tax payload."""
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and (line.price_unit > 0 or line.price_subtotal < 0)
            and not line.skip_etax
        )

    def _get_etax_line_amounts(self):
        """Return the amounts that belong to each individual e-Tax line.

        Preserve each line's signed base, tax and total, including deductions.
        Regular product amounts stay unchanged; the receiver can sum all lines
        without recalculating tax or applying the allowance a second time.
        """
        self.ensure_one()
        currency = self.currency_id
        amounts = {}
        for line in self._get_etax_invoice_lines():
            line_base = currency.round(line.price_subtotal)
            line_tax = currency.round(line.price_total - line.price_subtotal)
            line_total = currency.round(line.price_total)
            amounts[line.id] = (line_base, line_tax, line_total)
        return amounts

    def _get_etax_line_item_information(self):
        """Return e-Tax items shared by invoices and payment receipts."""
        self.ensure_one()
        line_amounts = self._get_etax_line_amounts()
        items = []
        for line in self._get_etax_invoice_lines():
            line_base, line_tax, line_total = line_amounts[line.id]
            # A positive down-payment invoice is a charge, not a deduction.
            is_allowance = line_base < 0
            items.append(
                self._prepare_etax_line_item(
                    line,
                    {
                        "product_code": line.product_id.default_code or "",
                        "product_name": line.product_id.name or line.name,
                        "product_price": 0.0
                        if is_allowance
                        else round(line.price_unit, 2),
                        "product_quantity": 1 if is_allowance else line.quantity,
                        "line_tax_type_code": "VAT" if line.tax_ids else "FRE",
                        "line_tax_rate": line.tax_ids[:1].amount or 0.0,
                        "line_base_amount": line_base,
                        "line_tax_amount": line_tax,
                        "line_allowance_charge_ind": "false" if is_allowance else "",
                        "line_allowance_actual_amount": (
                            abs(line_base) if is_allowance else 0.0
                        ),
                        "line_allowance_actual_currency_code": self.currency_id.name,
                        "line_total_amount": line_total,
                    },
                )
            )
        return items

    def _get_etax_line_total_amount(self):
        """Return the included line total after deductions and before VAT."""
        self.ensure_one()
        line_total = sum(line.price_subtotal for line in self._get_etax_invoice_lines())
        return self.currency_id.round(line_total)

    def _get_etax_final_amount_untaxed(self):
        """Return the e-Tax header total without changing invoice deductions.

        Debit and credit notes require the corrected amount after applying the
        adjustment to the original invoice.  Other documents keep using the
        line total so down-payment allowance lines remain deducted.
        """
        self.ensure_one()
        if self.debit_origin_id or self.reversed_entry_id:
            return self._get_additional_amount()[2]
        return self._get_etax_line_total_amount()

    def _prepare_etax_line_item(self, line, values):
        """Hook for report-specific unit prices and quantities."""
        self.ensure_one()
        return values

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
