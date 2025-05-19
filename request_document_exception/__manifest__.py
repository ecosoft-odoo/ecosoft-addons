# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Request Document - Exception",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["request_document", "base_exception"],
    "data": [
        "data/request_exception_data.xml",
        "security/ir.model.access.csv",
        "views/request_order_view.xml",
        "wizard/request_exception_confirm_view.xml",
    ],
    "installable": True,
}
