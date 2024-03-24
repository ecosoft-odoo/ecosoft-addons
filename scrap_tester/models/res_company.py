# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    enable_scrap_tester = fields.Boolean()
    scrap_tester_location_default = fields.Many2one(
        comodel_name="stock.location",
        domain="[('scrap_location', '=', True), ('company_id', 'in', [company_id, False])]",
        help="Select source location for auto create picking type",
    )
    scrap_account_template_default = fields.Many2one(
        comodel_name="account.move.template",
    )
    scrap_move_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("posted", "Posted"),
        ],
    )
