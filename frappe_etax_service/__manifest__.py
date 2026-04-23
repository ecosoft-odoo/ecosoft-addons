# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Connector to Frappe eTax service",
    "summary": "Integrate Odoo with Frappe e-Tax service",
    "version": "18.0.1.0.0",
    "author": "Kitti U., Ecosoft",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": [
        "account",
        "account_debit_note",
        "l10n_th_account_tax",
        "l10n_th_partner",
        "usability_api_connector",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/etax_doctype_code_data.xml",
        "data/etax_purpose_code_data.xml",
        "data/api_config_data.xml",
        # "data/server_action.xml",
        "views/res_config_settings.xml",
        "views/etax_menu.xml",
        "views/etax_purpose_code_views.xml",
        "views/etax_doctype_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "wizards/etax_doctype_wizard.xml",
        "wizards/etax_replacement_wizard.xml",
        "wizards/account_move_reversal_view.xml",
        "wizards/account_debit_note_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
