# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

ZORT_UPDATE_BOM_QTY = "zort_update_bom_qty"


class MrpBom(models.Model):
    _name = "mrp.bom"
    _inherit = ["mrp.bom", "common.base.api"]

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

    def _get_payload_globals_dict(self):
        result = super()._get_payload_globals_dict()
        boms = self.search([("product_tmpl_id.zort_product_id", "!=", False)])
        stocks_dict = {}
        for bom in boms:
            product_id = bom.product_tmpl_id.zort_product_id
            if product_id not in stocks_dict:
                stocks_dict[product_id] = {
                    "productid": product_id,
                    "stock": bom.qty_available,
                }
        result["bom_stocks"] = list(stocks_dict.values())
        return result

    def _hook_update_data(self, code_api, result):
        if code_api == ZORT_UPDATE_BOM_QTY:
            _logger.info("Updated BOM products' available stock to Zort")

    @api.model
    def update_bom_qty_to_zort(self):
        """Update BOM quantity to Zort as the product's available quantity."""
        synced_templates = self.env["product.template"].search(
            [("product_variant_ids.sync_with_zort", "=", True)]
        )
        boms = self.search(
            [
                ("product_tmpl_id", "in", synced_templates.ids),
                ("is_updated_qty_to_zort", "=", False),
            ]
        )

        if not boms:
            return
        return self.action_call_api(ZORT_UPDATE_BOM_QTY)
