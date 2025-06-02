# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Request Document - Purchase Request",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["request_document", "purchase_request"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/purchase_request_view.xml",
        "views/request_order_view.xml",
    ],
    "installable": True,
}
