# Copyright 2023 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "INET ETax Connector to Frappe",
    "author": "Kitti U.",
    "website": "https://github.com/kittiu/odoo_etax_inet",
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        # "data/server_actions.xml",
        "wizards/wizard_select_etax_doctype_view.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
}
