# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_scrap_tester = fields.Boolean(
        related="company_id.enable_scrap_tester",
        readonly=False,
    )
    scrap_tester_location_default = fields.Many2one(
        related="company_id.scrap_tester_location_default",
        readonly=False,
    )
    scrap_account_template_default = fields.Many2one(
        related="company_id.scrap_account_template_default",
        readonly=False,
    )
    scrap_move_state = fields.Selection(
        related="company_id.scrap_move_state",
        readonly=False,
    )
