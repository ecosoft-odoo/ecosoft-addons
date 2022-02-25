# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class CancelConfirm(models.TransientModel):
    _inherit = "cancel.confirm"

    def confirm_cancel(self):
        res = super().confirm_cancel()
        res_model = self._context.get("cancel_res_model")
        res_ids = self._context.get("cancel_res_ids")
        if res_model == "hr.expense.sheet":
            sheet = self.env[res_model].browse(res_ids)
            if sheet.advance_sheet_id:
                sheet.advance_sheet_id.clearing_residual += sheet.total_amount
        return res
