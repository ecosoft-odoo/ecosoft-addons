# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    email_etax = fields.Char(
        string="e-Tax Email",
        help="Email addresses for e-Tax delivery, separated by commas.",
    )
