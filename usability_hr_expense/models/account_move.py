# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_number = fields.Integer(compute="_compute_expense_number")

    def _compute_expense_number(self):
        for move in self:
            move.expense_number = len(
                move.line_ids.mapped("expense_id").mapped("sheet_id").ids
            )

    def action_get_expense(self):
        self.ensure_one()
        expense_report = self.line_ids.mapped("expense_id").mapped("sheet_id")
        action = {
            "name": _("Expenses"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense.sheet",
            "view_mode": "tree,form",
            "domain": [("id", "in", expense_report.ids)],
            "target": "current",
        }
        return action
