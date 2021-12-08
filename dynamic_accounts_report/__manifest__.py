# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Dynamic Financial Reports",
    "summary": "This module creates dynamic Balance Sheet, Proft and Loss",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Cybrosys Techno Solutions, Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ecosoft-addons",
    "depends": ["account_operating_unit"],
    "data": [
        "security/ir.model.access.csv",
        "data/account_financial_report_data.xml",
        "report/financial_report_template.xml",
        "views/account_financial_report_views.xml",
        "views/templates.xml",
    ],
    "qweb": [
        "static/src/xml/financial_reports_view.xml",
        "static/src/xml/general_ledger_view.xml",
    ],
    "installable": True,
    "maintainers": ["newtratip"],
    "development_status": "Alpha",
}
