# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Scrap Tester",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "summary": "Scrapping for Tester",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "category": "Warehouse Management",
    "depends": ["stock", "account_move_template"],
    "data": [
        "views/res_config_settings.xml",
        "views/stock_scrap_views.xml",
        "views/account_move_views.xml",
    ],
    "maintainers": ["Saran440"],
    "installable": True,
}
