# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability Purchase Guarantee - Operating Unit",
    "summary": "Manage fields and process on purchase guarantee",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "account_operating_unit",
        "l10n_th_gov_purchase_guarantee",
        "purchase_requisition_operating_unit",
        "purchase_operating_unit",
    ],
    "data": ["views/purchase_guarantee_views.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
