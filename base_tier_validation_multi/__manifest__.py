# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Base Tier Validation Multi",
    "summary": "Approve/Reject multiple records at once via tier validation",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "author": "Ecosoft",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "license": "AGPL-3",
    "depends": [
        "base_tier_validation",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/tier_validation_multi_wizard_view.xml",
        "views/tier_definition_views.xml",
    ],
    "maintainers": ["Saran440"],
}
