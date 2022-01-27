# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    salary_welfare = fields.Boolean()


class HRExpense(models.Model):
    _inherit = "hr.expense"

    salary_welfare = fields.Boolean(compute="_compute_salary_welfare", store=True)

    @api.depends("sheet_id")
    def _compute_salary_welfare(self):
        for exp in self:
            exp.salary_welfare = exp.sheet_id.salary_welfare
