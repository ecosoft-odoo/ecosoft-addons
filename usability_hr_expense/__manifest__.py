# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability HR Expense",
    "summary": "Manage fields on expense",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "budget_allocation_fund_advance_clearing",
        "budget_activity_advance_clearing",
        "hr_expense_operating_unit",
        "hr_expense_advance_clearing",
    ],
    "data": ["views/hr_expense_views.xml", "views/account_move_views.xml"],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
