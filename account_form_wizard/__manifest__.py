# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Form Wizard",
    "summary": "Manage view form with wizard",
    "version": "16.0.1.0.0",
    "category": "Tools",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_form_wizard_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
