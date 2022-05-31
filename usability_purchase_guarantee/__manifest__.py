# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability Purchase Guarantee",
    "summary": "Manage fields and process on purchase",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "l10n_th_gov_purchase_guarantee",
        "analytic_tag_dimension_enhanced",
        "budget_source_fund_purchase",
        "budget_source_fund_purchase_requisition",
    ],
    "data": ["views/purchase_guarantee_views.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
