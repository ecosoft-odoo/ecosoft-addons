# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MrpBom(models.Model):
    _name = "mrp.bom"
    _inherit = ["mrp.bom", "zort.api"]

    qty_available = fields.Float(
        related="product_tmpl_id.qty_available",
        string="On Hand Quantity",
        readonly=True,
    )

    @api.model
    def update_bom_qty_to_zort(self):
        """Update BOM quantity to Zort as the product's available quantity."""

        warehousecode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.warehouse_code")
            or "W0001"
        )

        stocks_dict = {}
        boms = self.search([("product_tmpl_id.zort_product_id", "!=", False)])
        for bom in boms:
            product_id = bom.product_tmpl_id.zort_product_id
            if product_id not in stocks_dict:
                stocks_dict[product_id] = {
                    "productid": product_id,
                    "stock": bom.qty_available,
                }

        # Convert dictionary values to list
        all_stocks = list(stocks_dict.values())

        if all_stocks:
            data = {"stocks": all_stocks}
            try:
                self._update_product_available_stock_list(warehousecode, data)
                _logger.info(
                    "Updated %d products' available stock to Zort", len(all_stocks)
                )
            except Exception as e:
                _logger.error(
                    "Failed to update products' available stock to Zort: %s", str(e)
                )
