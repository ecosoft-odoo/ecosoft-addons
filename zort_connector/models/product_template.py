import json
import logging

from markupsafe import Markup

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
    is_created_on_zort = fields.Boolean(
        string="Created on Zort",
        default=False,
        help="Indicates if this product has been created on Zort",
    )
    zort_product_id = fields.Char(
        help="The unique identifier of the product in Zort",
    )

    def action_create_product_on_zort(self):
        """Create product in Zort based on the current product template."""
        self.ensure_one()

        if not self.sync_with_zort:
            return

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

        self.is_created_on_zort = True
        self.zort_product_id = response.get("resDesc", "")

        if response.get("error"):
            _logger.error("Error creating product in Zort: %s", response.get("error"))
            return self._add_lognote_and_reload(
                title="Error",
                message="Failed to create product on Zort: {}".format(
                    response.get("error")
                ),
                data=data,
            )

        return self._add_lognote_and_reload(
            title="Success", message="Product created successfully on Zort.", data=data
        )

    def action_update_product_to_zort(self):
        """Update product in Zort based on the current product template."""
        self.ensure_one()
        if not self.is_created_on_zort:
            return

        data = {
            "name": self.name,
            "sellprice": self.list_price,
            "purchaseprice": self.standard_price,
            "unittext": self.uom_name,
            # "weight": self.weight, // we can uncomment later
            # "sell_vat_status": 0, // we can uncomment later
            # "purchase_vat_status": 0 // we can uncomment later
        }
        response = self._update_product(self.zort_product_id, data)

        if response.get("error"):
            _logger.error("Error updating product in Zort: %s", response.get("error"))
            return self._add_lognote_and_reload(
                title="Error",
                message="Failed to update product on Zort: {}".format(
                    response.get("error")
                ),
                data=data,
            )

        return self._add_lognote_and_reload(
            title="Success", message="Product updated successfully on Zort.", data=data
        )

    def action_update_qty_to_zort(self):
        pass

    def _add_lognote_and_reload(self, title: str, message: str, data: dict):
        """Add a log note to the chatter and return reload action."""
        formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
        message = Markup(f"<b>{title}</b>: {message}<br/><pre>{formatted_data}</pre>")
        self.message_post(body=message)
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
