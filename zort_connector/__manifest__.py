# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Zort Connector",
    "summary": "Connects Odoo with Zort",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["stock", "sale_management", "usability_api_connector"],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "data/api_config_data.xml",
        "data/ir_cron_data.xml",
        "data/ir_actions_server_data.xml",
        "data/product_data.xml",
        "data/partner_data.xml",
        "views/res_config_settings_view.xml",
        "views/zort_menu.xml",
        "views/zort_sync_log_views.xml",
        "views/zort_order_views.xml",
        "views/zort_ecommerce_channel_views.xml",
        "views/zort_product_view.xml",
        "views/product_product_view.xml",
        "views/sale_order_view.xml",
        "views/stock_picking_view.xml",
    ],
    "development_status": "Alpha",
    "maintainers": ["TheerayutEncoder", "Saran440"],
}
