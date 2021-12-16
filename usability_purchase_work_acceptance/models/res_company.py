# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    wa_fines_late_activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Late Delivery Fines Revenue Activity",
    )
