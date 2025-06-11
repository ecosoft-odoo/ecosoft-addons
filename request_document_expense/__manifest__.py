# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Request Document - Expense",
    "version": "18.0.1.0.3",
    "license": "AGPL-3",
    "category": "Accounting & Finance",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["request_document", "hr_expense"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/hr_expense_views.xml",
        "views/request_order_view.xml",
    ],
    "installable": True,
}
