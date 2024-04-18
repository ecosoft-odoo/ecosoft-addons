# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Report - Excel",
    "summary": "Add stock report excel",
    "version": "16.0.1.0.0",
    "author": "Ecosoft",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "stock",
        "report_xlsx_helper",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/report_data.xml",
        "reports/stock_location_report.xml",
        "wizards/stock_location_report_wizard_view.xml",
        "views/stock_menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_report_xlsx/static/src/scss/style_report.scss",
        ],
        "web.report_assets_common": [
            "stock_report_xlsx/static/src/scss/style_report.scss",
        ],
    },
    "license": "AGPL-3",
}
