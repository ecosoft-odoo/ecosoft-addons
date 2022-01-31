# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Account Financial Report Extension",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Tools",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "depends": ["base_report_extension", "account_financial_report"],
    "data": [
        "wizard/aged_partner_balance_wizard_view.xml",
        "wizard/general_ledger_wizard_view.xml",
        "wizard/open_items_wizard_view.xml",
        "wizard/trial_balance_wizard_view.xml",
    ],
    "installable": True,
}
