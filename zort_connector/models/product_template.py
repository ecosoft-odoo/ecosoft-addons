import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "zort.api"]

    sync_with_zort = fields.Boolean(
        string="Sync with Zort",
        default=False,
        help="Enable synchronization of this product with Zort API",
    )

    def action_update_create_product_on_zort(self):
        """Update or create product in Zort based on the current product template."""
        self.ensure_one()

        if not self.sync_with_zort:
            return

        try:
            data = {
                "sku": self.default_code,
                "name": self.name,
                "sellprice": self.list_price,
                "purchaseprice": self.standard_price,
                "unittext": self.uom_name,
                # "weight": self.weight, // we can uncomment later
                # "sell_vat_status": 0, // we can uncomment later
                # "purchase_vat_status": 0 // we can uncomment later
            }
            response = self._add_product(data)
            self._log_api_response(
                response_json={
                    "product_id": response.get("id"),
                    "status": response.get("status"),
                    "message": "Product created successfully",
                },
                func="action_update_create_zort",
                path="zort_connector/models/product_template.py",
                line=16,
            )
        except Exception as e:
            _logger.error("Error updating/creating product in Zort: %s", e)
            self._log_api_response(
                response_json={
                    "product_id": self.default_code,
                    "status": "error",
                    "error": str(e),
                },
                func="action_update_create_zort",
                level="error",
                path="zort_connector/models/product_template.py",
                line=16,
            )

    def action_update_qty_to_zort(self):
        pass
