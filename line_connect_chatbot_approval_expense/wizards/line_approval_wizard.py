# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class LINEApprovalWizard(models.TransientModel):
    _inherit = "line.approval.wizard"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "hr.expense.sheet":
            sheet_model = self.env.ref("hr_expense.model_hr_expense_sheet")
            line_template_default = self.env["line.template"].search(
                [
                    ("template_model", "=", sheet_model.id),
                    ("template_default", "=", True),
                ]
            )
            active_ids = self.env.context.get("active_ids", [])
            sheet = self.env["hr.expense.sheet"].browse(active_ids)
            template = (
                line_template_default.id if len(line_template_default) == 1 else False
            )
            res.update(
                {
                    "model": sheet_model.id,
                    "template_id": template,
                    "partner_approval": sheet.user_id.partner_id.id,
                }
            )
        return res

    def action_approval_line(self):
        """Auto submit to manager"""
        res = super().action_approval_line()
        if self.env.context.get("active_model") == "hr.expense.sheet":
            active_ids = self.env.context.get("active_ids")
            sheets = self.env["hr.expense.sheet"].browse(active_ids)
            sheets.action_submit_sheet()
        return res
