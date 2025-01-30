# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Line Connect - Expense Chat Bot Approval",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "summary": "LINE Expense Approval",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "category": "Report",
    "depends": [
        "line_connect_chatbot_approval",
        "hr_expense",
        "hr_expense_sequence",
    ],
    "data": [
        "data/line_template_data.xml",
        "views/hr_expense_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
