# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Withholding Tax Certificate Form Sequence",
    "summary": "Define sequence for WHT Cert.",
    "version": "15.0.1.0.0",
    "category": "Localization / Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "base_sequence_option",
        "l10n_th_account_wht_cert_form",
    ],
    "data": [
        "data/withholding_tax_cert_data.xml",
        "reports/withholding_tax_cert_form_view.xml",
        "views/withholding_tax_cert_view.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "/l10n_th_account_wht_cert_form_sequence/static/src/scss/style_report.scss",
        ],
    },
    "installable": True,
    "maintainers": ["ps-tubtim"],
    "development_status": "Alpha",
}
