# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ZortProduct(models.Model):
    _name = "zort.product"
    _description = "Zort Product"
    _order = "id desc"

    name = fields.Char(required=True)
    id_zort_product = fields.Char(string="Zort Product ID", required=True)
    description = fields.Text()
    sku = fields.Char(string="Code")
    sell_price = fields.Float(string="Sale Price", digits="Product Price")
    purchase_price = fields.Float(digits="Product Price")
    unit_text = fields.Char(string="Unit")
    image_url = fields.Char(string="Image URL")
    active = fields.Boolean(default=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Odoo Product",
        ondelete="set null",
    )

    _sql_constraints = [
        (
            "id_zort_product_uniq",
            "UNIQUE(id_zort_product)",
            "Zort Product ID must be unique.",
        ),
        ("sku_uniq", "UNIQUE(sku)", "SKU must be unique."),
    ]
