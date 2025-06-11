# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    request_type = fields.Selection(
        selection_add=[("expense", "Expense")],
        ondelete={"expense": "cascade"},
    )
    expense_sheet_ids = fields.One2many(
        comodel_name="hr.expense.sheet",
        inverse_name="request_document_id",
    )

    @api.depends(
        "expense_sheet_ids", "expense_sheet_ids.name", "expense_sheet_ids.total_amount"
    )
    def _compute_document(self):
        res = super()._compute_document()
        for rec in self:
            sheet_id = rec.expense_sheet_ids
            if sheet_id:
                rec.name_document = sheet_id.name
                rec.total_amount_document = sheet_id.total_amount
        return res

    def _update_state_expense(self, sheets, state_config):
        self.ensure_one()
        sheets.action_approve_expense_sheets()
        if state_config == "post":
            sheets.action_sheet_move_post()

    def _create_expense(self):
        self.ensure_one()
        sheet = self.expense_sheet_ids.with_context(allow_edit=1)
        # Change to submit
        sheet.action_submit_sheet()
        # Check config
        state_config = self.company_id.request_document_ex_state
        if state_config != "submit":
            self._update_state_expense(sheet, state_config)
        return

    def unlink(self):
        # Delete draft sheet
        self.expense_sheet_ids.unlink()
        return super().unlink()

    def open_request_document(self):
        res = super().open_request_document()
        if self.request_type == "expense":
            ctx = self.env.context.copy()
            ctx.update(
                {
                    "default_request_document_id": self.id,
                    "invisible_header": 1,
                    "create": 0,  # Not allow create
                }
            )
            if self.state == "draft":
                ctx["allow_edit"] = 1

            return {
                "type": "ir.actions.act_window",
                "views": [(False, "form")],
                "view_mode": "form",
                "res_model": "hr.expense.sheet",
                "res_id": self.expense_sheet_ids.id,  # should be 1 only
                "context": ctx,
                "target": "new",
            }
        return res
