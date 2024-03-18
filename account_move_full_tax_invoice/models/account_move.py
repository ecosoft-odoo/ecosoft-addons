# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    move_full_tax_id = fields.Many2one(
        comodel_name="account.move",
        copy=False,
        readonly=True,
        string="Invoice Full Tax",
    )
    is_tax_abb = fields.Boolean(
        string="Tax (ABB)",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )
