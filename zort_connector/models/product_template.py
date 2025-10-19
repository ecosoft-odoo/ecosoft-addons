# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import base64
import json
import logging

import requests
from markupsafe import Markup

from odoo import _, fields, models

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

        self.is_created_on_zort = True
        self.zort_product_id = response.get("resDesc", "")

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
        self.ensure_one()
        if not self.is_created_on_zort:
            return

        data = {
            "stocks": [
                {
                    "sku": self.default_code,
                    "stock": self.qty_available,
                }
            ]
        }
        response = self._update_product_available_stock_list(
            warehousecode="W0001", data=data
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

    def _add_lognote_and_reload(self, title: str, message: str, data: dict):
        """Add a log note to the chatter and return reload action."""
        formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
        message = Markup(f"<b>{title}</b>: {message}<br/><pre>{formatted_data}</pre>")
        self.message_post(body=message)
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def fetch_product_image_from_zort(
        self, sku_list: str = "", product_id_list: str = ""
    ) -> dict:
        """
        Fetch product images from Zort for given SKU or product ID list.
        Returns a dict mapping product IDs to image URLs.
        """
        response = self._get_products(skulist=sku_list, productidlist=product_id_list)
        if response.get("error"):
            _logger.error(
                "Error fetching product images from Zort: %s", response.get("error")
            )
            return {}
        return {
            str(product.get("id")): product.get("imagepath")
            for product in response.get("list", [])
            if product.get("id") and product.get("imagepath")
        }

    def action_fetch_and_update_image_from_zort(self):
        """Fetch and update product images from Zort for products linked to Zort."""
        self.ensure_one()
        if not self.zort_product_id:
            return
        image_map = self.fetch_product_image_from_zort(
            product_id_list=self.zort_product_id
        )
        image_url = image_map.get(self.zort_product_id)
        if not image_url:
            _logger.warning(
                "No image found for product ID %s on Zort", self.zort_product_id
            )
            self.message_post(body=_("No image found for this product on Zort."))
            return
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = base64.b64encode(response.content).decode("utf-8")
            self.image_1920 = image_data
            _logger.info(
                "Image updated successfully from Zort for product %s", self.name
            )
            self.message_post(body=_("Product image updated successfully from Zort."))
        except requests.RequestException as e:
            _logger.error("Error fetching image from Zort: %s", str(e))
            self.message_post(body=_("Failed to fetch image from Zort: %s", str(e)))

    @staticmethod
    def decode_image_url(image_url: str):
        """Set the product image."""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = base64.b64encode(response.content).decode("utf-8")
            return image_data
        except requests.RequestException as e:
            _logger.error("Error fetching image from Zort: %s", str(e))
            return None
