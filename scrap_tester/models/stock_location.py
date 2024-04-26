# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    tester_location = fields.Boolean(
        string="Is a Tester Location?",
        default=False,
        help="Check this box to allow using this location to put tester goods.",
    )
