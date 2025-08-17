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
