# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Usability Auditlog",
    "summary": "Used to customize auditlog",
    "version": "14.0.1.0.0",
    "category": "HII",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/ecosoft-addons",
    "license": "AGPL-3",
    "depends": [
        "auditlog",
        "budget_control",
        "base_user_role",
        "base_tier_validation",
        "budget_allocation",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/auditlog_rule.xml",
        "data/ir_actions_server.xml",
        "views/auditlog_view.xml",
        "views/budget_control_views.xml",
        "views/budget_allocation_views.xml",
    ],
    "installable": True,
}
