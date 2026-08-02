# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Product Image from URL",
    "summary": "Download product images from URLs into standard Odoo fields",
    "version": "18.0.1.0.0",
    "category": "Product",
    "author": "Ecosoft",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "license": "AGPL-3",
    "depends": ["product"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/product_product_views.xml",
    ],
    "installable": True,
}
