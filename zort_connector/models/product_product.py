# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import json
import logging

import requests
from markupsafe import Markup

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "zort.api"]

    zort_product_ids = fields.One2many(
        comodel_name="zort.product",
        inverse_name="product_id",
        string="Zort Products",
    )
    sync_with_zort = fields.Boolean(
        string="Sync with Zort",
        default=False,
        help="Enable synchronization of this product with Zort API",
    )

    def action_fetch_and_update_image_from_zort(self):
        """Fetch and update product images from Zort."""
        self.ensure_one()
        if not self.zort_product_ids:
            return
        zort_product = self.zort_product_ids[0]
        if not zort_product.image_url:
            return

        try:
            response = requests.get(zort_product.image_url, timeout=10)
            response.raise_for_status()

            image_data = base64.b64encode(response.content)
            self.image_1920 = image_data
            _logger.info(
                "Successfully updated image for product %s from Zort.",
                self.display_name,
            )

        except requests.RequestException as e:
            _logger.error(
                "Failed to fetch image from Zort for product %s: %s",
                self.display_name,
                str(e),
            )

    def _add_lognote_and_reload(self, title: str, message: str, data: dict):
        """Add a log note to the chatter and return reload action."""
        formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
        message = Markup(f"<b>{title}</b>: {message}<br/><pre>{formatted_data}</pre>")
        self.message_post(body=message)
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_create_product_on_zort(self):
        """Create product in Zort based on the current product variant."""
        self.ensure_one()

        if not self.sync_with_zort:
            return

        data = {
            "sku": self.default_code,
            "name": self.name,
            "sellprice": self.list_price,
            "purchaseprice": self.standard_price,
            "unittext": self.uom_name,
            # "weight": self.weight, # we can uncomment later
            # "sell_vat_status": 0, # we can uncomment later
            # "purchase_vat_status": 0 # we can uncomment later
        }
        response = self._add_product(data)

        if response.get("error"):
            _logger.error("Error creating product in Zort: %s", response.get("error"))
            return self._add_lognote_and_reload(
                title="Error",
                message="Failed to create product on Zort: {}".format(
                    response.get("error")
                ),
                data=data,
            )
        elif response.get("resCode") != "200":
            _logger.error(
                "Error creating product in Zort: %s",
                response.get("resDesc", "Unknown error"),
            )
            return self._add_lognote_and_reload(
                title="Error",
                message=(
                    "Failed to create product on Zort: {}\n"
                    "Please check on Zort, the product may have already been created.\n"
                    "If the product was created, you should update the Zort Product "
                    "with the product ID from Zort."
                ).format(response.get("resDesc", "Unknown error")),
                data=data,
            )

        # If api call is successful "resDesc" will contain the product ID in Zort
        if response.get("resDesc", ""):
            # Create zort.product record
            self.env["zort.product"].create(
                {
                    "product_id": self.id,
                    "id_zort_product": response.get("resDesc", ""),
                    "sku": self.default_code,
                    "unittext": self.uom_name,
                    "name": self.name,
                }
            )

        return self._add_lognote_and_reload(
            title="Success", message="Product created successfully on Zort.", data=data
        )

    def action_update_product_to_zort(self):
        """Update product in Zort based on the current product variant."""
        self.ensure_one()

        data = {
            "name": self.name,
            "sellprice": self.list_price,
            "purchaseprice": self.standard_price,
            "unittext": self.uom_name,
            # "weight": self.weight, // we can uncomment later
            # "sell_vat_status": 0, // we can uncomment later
            # "purchase_vat_status": 0 // we can uncomment later
        }
        zort_product = self.env["zort.product"].search(
            [("product_id", "=", self.id)], limit=1
        )
        if not zort_product:
            return

        response = self._update_product(zort_product.id_zort_product, data)

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
        self.ensure_one()

        data = {
            "stocks": [
                {
                    "sku": self.default_code,
                    "stock": self.qty_available,
                }
            ]
        }
        warehousecode = self.env.company.zort_warehouse_code or "W0001"
        response = self._update_product_available_stock_list(
            warehousecode=warehousecode, data=data
        )

        if response.get("error"):
            _logger.error("Error updating stock in Zort: %s", response.get("error"))
            return self._add_lognote_and_reload(
                title="Error",
                message="Failed to update stock on Zort: {}".format(
                    response.get("error")
                ),
                data=data,
            )

        _logger.info("Stock updated successfully on Zort: %s", response)
        return self._add_lognote_and_reload(
            title="Success", message="Stock updated successfully on Zort.", data=data
        )
