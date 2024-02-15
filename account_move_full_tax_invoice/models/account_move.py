# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    origin_invoice_ftx_move_id = fields.Many2one(
        comodel_name="account.move",
        readonly=True,
        string="Origin Invoice Full Tax",
    )
