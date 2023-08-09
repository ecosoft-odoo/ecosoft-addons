# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import ValidationError


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids
        for rec in moves:
            # Expense case journal only (not include payment)
            sheet = rec.line_ids.mapped("expense_id").mapped("sheet_id")
            sheet_not_post = sheet.filtered(lambda l: l.state != "post")
            rec_pay_lines = rec._get_receivable_payable_lines()
            if (
                rec.move_type in ["in_invoice", "out_invoice"]
                and (
                    rec_pay_lines.matched_debit_ids or rec_pay_lines.matched_credit_ids
                )
            ) or (sheet and sheet_not_post and not rec.payment_id):
                raise ValidationError(
                    _("You cannot reset to draft / reverse reconciled entries.")
                )
        res = super().reverse_moves()
        # Overwite payment state to reversed
        moves.with_context(bypass_lockdate=1).write({"payment_state": "reversed"})
        return res
