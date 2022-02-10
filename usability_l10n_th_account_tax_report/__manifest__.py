# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability Thai Localization - VAT and Withholding Tax Reports",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "l10n_th_account_tax_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/paper_format.xml",
        "data/report_data.xml",
        "reports/report_rd_withholding_tax_qweb.xml",
        "views/withholding_tax_cert.xml",
        "wizard/rd_withholding_tax_report_wizard_view.xml",
    ],
    "installable": True,
    "maintainers": ["ps-tubtim"],
    "development_status": "Alpha",
}
