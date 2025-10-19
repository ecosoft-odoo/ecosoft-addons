# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_platform_code = fields.Char(
        string="Customer Platform",
        help=(
            "Platform where the customer was acquired "
            "(e.g., lazada, shopee). Use lowercase."
        ),
    )
