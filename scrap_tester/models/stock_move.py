# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    tester_scrapped = fields.Boolean(
        string="Tester Scrapped", related="location_dest_id.tester_location", store=True
    )
