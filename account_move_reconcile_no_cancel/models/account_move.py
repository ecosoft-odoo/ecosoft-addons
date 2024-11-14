# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _check_fiscalyear_lock_date(self):
        if self._context.get("bypass_lockdate"):
            return True
        return super()._check_fiscalyear_lock_date()

    def _check_move_reconciled(self, action=""):
        for rec in self:
            matched_debit_credit_ids = rec.line_ids.mapped(
                "matched_debit_ids"
            ) | rec.line_ids.mapped("matched_credit_ids")
            if matched_debit_credit_ids:
                # Check reconciled from invoice and expense move (not included payment)
                sheet = rec.line_ids.mapped("expense_id.sheet_id")
                if rec.move_type in [
                    f"{x}_{y}" for x in ["in", "out"] for y in ["invoice", "refund"]
                ] or (sheet and not rec.payment_id):
                    raise ValidationError(
                        _("You cannot {} reconciled entries.").format(action)
                    )
        return True

    def button_draft(self):
        self._check_move_reconciled(action="reset to draft")
        return super().button_draft()

    def button_cancel(self):
        self._check_move_reconciled(action="cancel")
        return super().button_cancel()
