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
    is_updated_qty_to_zort = fields.Boolean(
        string="Update Qty to Zort",
        default=False,
        help="Indicates whether to update the BOM quantity to Zort.",
    )

    @api.model
    def update_bom_qty_to_zort(self):
        """Update BOM quantity to Zort as the product's available quantity."""

        warehousecode = self.env.company.zort_warehouse_code or "W0001"

        stocks_dict = {}
        synced_templates = self.env["product.template"].search(
            [("product_variant_ids.sync_with_zort", "=", True)]
        )
        boms = self.search(
            [
                ("product_tmpl_id", "in", synced_templates.ids),
                ("is_updated_qty_to_zort", "=", False),
            ]
        )

        for bom in boms:
            product_id = bom.product_tmpl_id.product_variant_ids[0].id
            zort_product = self.env["zort.product"].search(
                [("product_id", "=", product_id)]
            )
            if product_id not in stocks_dict:
                stocks_dict[product_id] = {
                    "productid": zort_product.id_zort_product,
                    "stock": bom.qty_available,
                }

        # Convert dictionary values to list
        all_stocks = list(stocks_dict.values())

        if all_stocks:
            data = {"stocks": all_stocks}
            try:
                response = self._update_product_available_stock_list(
                    warehousecode, data
                )

                if "error" in response:
                    _logger.error(
                        "API error updating products' available stock to Zort: %s",
                        response["error"],
                    )
                    return False
                else:
                    _logger.info(
                        "Updated %d products' available stock to Zort", len(all_stocks)
                    )
                    boms.write({"is_updated_qty_to_zort": True})
                    return True

            except Exception as e:
                _logger.error(
                    "Failed to update products' available stock to Zort: %s", str(e)
                )
                return False
