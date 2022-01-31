# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DataMapType(models.Model):
    _inherit = "data.map.type"

    model = fields.Selection(
        selection_add=[
            ("aged_partner_balance", "Aged Partner Balance"),
            ("general_ledger", "General Ledger"),
            ("open_items", "Open Items"),
            ("trial_balance", "Trial Balance"),
        ],
        ondelete={
            "aged_partner_balance": "cascade",
            "general_ledger": "cascade",
            "open_items": "cascade",
            "trial_balance": "cascade",
        },
    )
