# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_withholding_tax_entry(self):
        move_vals = super()._prepare_withholding_tax_entry()
        if self.operating_unit_id:
            move_vals["operating_unit_id"] = self.operating_unit_id.id
        return move_vals
