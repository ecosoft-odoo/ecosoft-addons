# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from odoo.tests.common import TransactionCase


class TestProductImageUrl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Some deployments restrict product creation in an inherited model.
        # This framework context also keeps module-data product creation usable.
        cls.ProductTemplate = cls.env["product.template"].with_context(
            install_module=True
        )
        cls.image_content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNg"
            "YAAAAAMAASsJTYQAAAAASUVORK5CYII="
        )
        image = Image.new("RGB", (2048, 1024), color="red")
        image_buffer = BytesIO()
        image.save(image_buffer, format="PNG")
        cls.large_image_content = image_buffer.getvalue()

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "product_image_url.max_size", "1024"
        )

    def test_create_downloads_image_automatically(self):
        with patch.object(
            type(self.env["product.template"]),
            "_download_image_url",
            return_value=self.image_content,
        ) as download:
            product = self.ProductTemplate.create(
                {
                    "name": "URL image product",
                    "image_url": " https://example.com/product.png ",
                }
            )

        self.assertEqual(product.image_url, "https://example.com/product.png")
        self.assertTrue(product.image_1920)
        download.assert_called_once_with("https://example.com/product.png")

    def test_changing_url_downloads_new_image(self):
        product = self.ProductTemplate.create({"name": "Test product"})
        with patch.object(
            type(product),
            "_download_image_url",
            return_value=self.image_content,
        ) as download:
            product.image_url = "https://example.com/new.png"

        self.assertTrue(product.image_1920)
        download.assert_called_once_with("https://example.com/new.png")

    def test_changing_url_from_variant_downloads_template_image(self):
        template = self.ProductTemplate.create({"name": "Test product"})
        with patch.object(
            type(template),
            "_download_image_url",
            return_value=self.image_content,
        ) as download:
            template.product_variant_id.image_url = "https://example.com/variant.png"

        self.assertTrue(template.image_1920)
        download.assert_called_once_with("https://example.com/variant.png")

    def test_clearing_url_keeps_downloaded_image(self):
        product = self.ProductTemplate.create(
            {"name": "Test product", "image_1920": base64.b64encode(self.image_content)}
        )
        product.image_url = False
        self.assertTrue(product.image_1920)

    def test_configured_max_size_resizes_downloaded_image(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "product_image_url.max_size", "512"
        )
        with patch.object(
            type(self.env["product.template"]),
            "_download_image_url",
            return_value=self.large_image_content,
        ):
            product = self.ProductTemplate.create(
                {
                    "name": "Resized URL image product",
                    "image_url": "https://example.com/product.png",
                }
            )

        stored_image = base64.b64decode(product.with_context(bin_size=False).image_1920)
        with Image.open(BytesIO(stored_image)) as image:
            self.assertEqual(image.size, (512, 256))

    def test_invalid_configured_size_falls_back_to_1024(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "product_image_url.max_size", "invalid"
        )
        self.assertEqual(
            self.ProductTemplate._get_configured_image_max_size(),
            1024,
        )

    def test_external_url_mode_is_not_part_of_product_model(self):
        self.assertNotIn("image_url_mode", self.ProductTemplate._fields)
