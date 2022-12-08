# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Tier Validation",
    "summary": "Extends the functionality of Account Payment to "
    "support a tier validation process.",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "account",
        "base_tier_validation_server_action",
    ],
    "data": [
        "views/account_payment_views.xml",
    ],
    "demo": ["demo/account_payment_tier_definition.xml"],
    "installable": True,
}
