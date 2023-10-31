# Copyright 2023 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Connector to Frappe eTax service",
    "version": "15.0.1.0.0",
    "author": "Kitti U.",
    "license": "AGPL-3",
    "depends": [
        "account",
        "account_debit_note",
        "l10n_th_account_tax",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/purpose_code_data.xml",
        "data/cron.xml",
        "wizards/wizard_select_etax_doctype_view.xml",
        "wizards/account_move_reversal_view.xml",
        "wizards/account_debit_note_view.xml",
        "wizards/wizard_select_replacement_purpose.xml",
        "views/account_move_views.xml",
        "views/res_config_settings.xml",
        "views/purpose_code_views.xml",
        "views/doctype_views.xml",
    ],
    "installable": True,
}
