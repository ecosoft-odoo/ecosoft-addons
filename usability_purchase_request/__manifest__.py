# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability Purchase Request",
    "summary": "Manage fields on purchase request",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "budget_activity_purchase_request",
        "budget_source_fund_purchase_request",
        "purchase_request_operating_unit",
    ],
    "data": ["views/purchase_request_view.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
