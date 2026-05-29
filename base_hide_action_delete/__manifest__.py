# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Hide Action Delete",
    "summary": "Hide Delete from the Action menu, configurable per security group",
    "version": "18.0.2.0.0",
    "category": "Technical",
    "author": "Ecosoft",
    "license": "AGPL-3",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["web"],
    "data": [
        "security/base_hide_action_delete_groups.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "base_hide_action_delete/static/src/js/hide_delete_action.esm.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
