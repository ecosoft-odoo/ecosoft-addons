# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import logging

import requests
from markupsafe import Markup

from odoo import fields, models

_logger = logging.getLogger(__name__)

ZORT_CREATE_PRODUCT = "zort_create_product"
ZORT_UPDATE_PRODUCT = "zort_update_product"
ZORT_UPDATE_QTY = "zort_update_qty"
ZORT_FETCH_IMAGE = "zort_fetch_product_image"


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "common.base.api"]

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

    def decode_image_url(self, image_url):
        """Set the product image."""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = base64.b64encode(response.content).decode("utf-8")
            return image_data
        except requests.RequestException as e:
            _logger.error("Error fetching image from Zort: %s", str(e))
            return None

    def _hook_update_data(self, code_api, result):
        """Handle Zort API responses for product operations."""
        if code_api == ZORT_CREATE_PRODUCT:
            res_code = result.get("resCode", "")
            zort_product_id = result.get("resDesc", "")
            if res_code == "200" and zort_product_id:
                self.env["zort.product"].create(
                    {
                        "product_id": self.id,
                        "id_zort_product": zort_product_id,
                        "sku": self.default_code,
                        "unit_text": self.uom_name,
                        "name": self.name,
                    }
                )
                self.message_post(
                    body=Markup("<b>Success</b>: Product created successfully on Zort.")
                )
            else:
                desc = result.get("resDesc", "Unknown error")
                _logger.error("Error creating product in Zort: %s", desc)
                self.message_post(
                    body=Markup(
                        f"<b>Error</b>: Failed to create product on Zort: {desc}<br/>"
                        "Please check on Zort, the product may have "
                        "already been created.<br/> If the product was created, "
                        "you should update the Zort Product with the "
                        "product ID from Zort."
                    )
                )
        elif code_api == ZORT_UPDATE_PRODUCT:
            self.message_post(
                body=Markup("<b>Success</b>: Product updated successfully on Zort.")
            )
        elif code_api == ZORT_UPDATE_QTY:
            self.message_post(
                body=Markup("<b>Success</b>: Stock updated successfully on Zort.")
            )
        elif code_api == ZORT_FETCH_IMAGE:
            if result.get("error"):
                _logger.warning(
                    "Error fetching product from Zort: %s", result.get("error")
                )
                self.message_post(
                    body=Markup(
                        "<b>Warning</b>: No image found for this product on Zort."
                    )
                )
                return
            products = result.get("list", [])
            image_url = products[0].get("imagepath", "") if products else ""
            if not image_url:
                _logger.warning(
                    "No image found for product ID %s on Zort", self.zort_product_id
                )
                self.message_post(
                    body=Markup(
                        "<b>Warning</b>: No image found for this product on Zort."
                    )
                )
                return
            image_data = self.decode_image_url(image_url)
            if image_data:
                self.image_1920 = image_data
                _logger.info(
                    "Image updated successfully from Zort for product %s", self.name
                )
                self.message_post(
                    body=Markup(
                        "<b>Success</b>: Product image updated successfully from Zort."
                    )
                )
            else:
                self.message_post(
                    body=Markup("<b>Error</b>: Failed to download image from Zort.")
                )

    def action_create_product_on_zort(self):
        """Create product in Zort via common.base.api. Result is handled in
        _hook_update_data. Always returns a form reload so the UI reflects the
        updated zort_product_id / is_created_on_zort values."""
        self.ensure_one()
        if not self.sync_with_zort:
            return
        return self.action_call_api(ZORT_CREATE_PRODUCT)

    def action_update_product_to_zort(self):
        """Update product in Zort via common.base.api. Result is handled in
        _hook_update_data."""
        self.ensure_one()
        zort_product = self.env["zort.product"].search(
            [("product_id", "=", self.id)], limit=1
        )
        if not zort_product:
            return
        return self.action_call_api(ZORT_UPDATE_PRODUCT)

    def action_update_qty_to_zort(self):
        """Update stock quantity in Zort via common.base.api. Result is handled in
        _hook_update_data. Always returns a form reload so the UI reflects any
        updated values."""
        self.ensure_one()
        return self.action_call_api(ZORT_UPDATE_QTY)

    def action_fetch_and_update_image_from_zort(self):
        """Fetch and update product images from Zort for products linked to Zort."""
        self.ensure_one()
        zort_product = self.zort_product_ids[0]
        if not zort_product.image_url:
            return
        return self.action_call_api(ZORT_FETCH_IMAGE)
