# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Usability Base Exception",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "license": "AGPL-3",
    "category": "Tools",
    "depends": [
        "purchase_exception",
        "purchase",
        "purchase_request",
        "account_move_exception",
        "account",
    ],
    "data": [
        "data/exceptions.xml",
        "views/purchase_views.xml",
        "views/invoice_views.xml",
    ],
    "installable": True,
    "development_status": "Beta",
    "maintainers": ["kittiu"],
}
