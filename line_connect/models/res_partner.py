# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    line_access_token = fields.Char(
        string="LINE Access Token",
        help="Access token for LINE Messaging API.",
        tracking=True,
    )
