# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Base Print Wizard",
    "version": "18.0.1.0.0",
    "summary": "Add wizard when use print action",
    "category": "Tools",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_actions_report_view.xml",
        "wizard/base_print_wizard_view.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
    "development_status": "Alpha",
}
