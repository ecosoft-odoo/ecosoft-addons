# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_receivable_payable_lines(self):
        return self.line_ids.filtered(
            lambda l: l.account_internal_type in ["receivable", "payable"],
        )

    def button_draft(self):
        for rec in self:
            rec_pay_lines = rec._get_receivable_payable_lines()
            # Expense case journal only (not include payment)
            sheet = rec.line_ids.mapped("expense_id").mapped("sheet_id")
            sheet_not_post = sheet.filtered(lambda l: l.state != "post")
            if (
                rec.move_type in ["in_invoice", "out_invoice"]
                and (
                    rec_pay_lines.matched_debit_ids or rec_pay_lines.matched_credit_ids
                )
            ) or (sheet and sheet_not_post and not rec.payment_id):
                raise ValidationError(
                    _("You cannot reset to draft reconciled entries.")
                )
        return super().button_draft()

    def button_cancel(self):
        for rec in self:
            rec_pay_lines = rec._get_receivable_payable_lines()
            if rec.move_type in ["in_invoice", "out_invoice"] and (
                rec_pay_lines.matched_debit_ids or rec_pay_lines.matched_credit_ids
            ):
                raise ValidationError(_("You cannot cancel reconciled entries."))
        return super().button_cancel()
