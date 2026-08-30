# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    zort_connector_enabled = fields.Boolean(
        default=False,
    )
    zort_api_key = fields.Char()
    zort_api_secret = fields.Char()
    zort_store_name = fields.Char()
    zort_warehouse_code = fields.Char(
        default="W0001",
    )
    zort_default_tax_id = fields.Many2one(
        comodel_name="account.tax",
        check_company=True,
    )
