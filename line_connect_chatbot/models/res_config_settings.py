# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    line_channel_access_token = fields.Char(
        string="Channel Access Token", config_parameter="line.channel_access_token"
    )
    line_channel_secret = fields.Char(
        string="Channel Secret", config_parameter="line.channel_secret"
    )
