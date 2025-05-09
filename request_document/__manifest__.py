# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Request Document",
    "version": "18.0.2.0.0",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/request_order_security.xml",
        "data/request_order_data.xml",
        "views/request_menuitem.xml",
        "views/res_config_settings_views.xml",
        "views/request_order_view.xml",
        "views/request_document_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
