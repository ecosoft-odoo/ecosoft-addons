# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Accounting - Tax ABB",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "summary": "change ABB to full tax invoice",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "category": "Accounting",
    "depends": ["account"],
    "data": [
        "data/account_journal_data.xml",
        "views/account_move_view.xml",
        "views/res_partner_views.xml",
    ],
    "maintainers": ["Saran440"],
    "installable": True,
}
