# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Request Document - Accounting",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["request_document", "account"],
    "data": [
        "views/account_move_views.xml",
        "views/request_order_view.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
