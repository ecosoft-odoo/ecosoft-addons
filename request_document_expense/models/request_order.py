# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestOrder(models.Model):
    _inherit = "request.order"

    expense_sheet_counts = fields.Integer(
        string="Expense Sheet Count",
        compute="_compute_expense_sheet_counts",
    )

    @api.depends("line_ids.expense_sheet_ids")
    def _compute_expense_sheet_counts(self):
        for rec in self:
            rec.expense_sheet_counts = len(rec.line_ids.mapped("expense_sheet_ids"))

    def action_open_expense_sheet(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "hr_expense.action_hr_expense_sheet_all"
        )
        action["domain"] = [("id", "in", self.line_ids.mapped("expense_sheet_ids").ids)]
        return action
