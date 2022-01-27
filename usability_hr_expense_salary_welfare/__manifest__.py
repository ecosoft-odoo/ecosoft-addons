# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability - Salary Welfare",
    "summary": "Allow do transaction with other OU on expense",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "hr_expense_operating_unit",
        "usability_hr_expense",
    ],
    "data": [
        "security/hr_expense_security.xml",
        "security/ir_rule.xml",
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
