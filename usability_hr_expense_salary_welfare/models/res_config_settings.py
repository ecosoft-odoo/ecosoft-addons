# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_salary_welfare = fields.Boolean(
        string="Manage Salary & Welfare",
        implied_group="hr_expense_widget_o2m.group_hr_expense_widget_o2m",
    )
