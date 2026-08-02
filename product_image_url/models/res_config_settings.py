# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_image_url_max_size = fields.Selection(
        selection=[
            ("512", "512 px"),
            ("1024", "1024 px"),
            ("1920", "1920 px"),
        ],
        string="Maximum Image Size",
        required=True,
        default="1024",
        config_parameter="product_image_url.max_size",
        help=(
            "Maximum width and height for product images downloaded from a URL. "
            "Existing product images are not modified."
        ),
    )
