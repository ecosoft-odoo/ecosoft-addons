# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "zort_connector",
    "summary": "Connects Odoo with Zort",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "maintainers": ["theerayuta@ecosoft.co.th"],
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["base", "stock", "sale_management"],
    "data": [
        "data/ir_actions_server_data.xml",
        "data/ir_cron_data.xml",
        "data/partner_data.xml",
        "data/product_data.xml",
        "views/res_config_settings_view.xml",
        "views/sale_order_view.xml",
        "views/product_template_view.xml",
        "views/res_partner_view.xml",
    ],
}
