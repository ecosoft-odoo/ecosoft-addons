# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Report - Queue Job",
    "summary": "Used job queue to export excel",
    "version": "16.0.1.0.0",
    "author": "Ecosoft",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "stock_report_xlsx",
        "report_async",
    ],
    "data": [
        "wizards/stock_inventory_report_wizard_view.xml",
    ],
    "license": "AGPL-3",
}
