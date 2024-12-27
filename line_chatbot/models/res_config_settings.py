# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    line_connect = fields.Boolean(related="company_id.line_connect", readonly=False)
    line_channel_access_token = fields.Char(
        string="Channel Access Token", config_parameter="line.channel_access_token"
    )
    line_channel_secret = fields.Char(
        string="Channel Secret", config_parameter="line.channel_secret"
    )
    line_login_channel_id = fields.Char(
        string="LINE Login Channel ID", config_parameter="line.login_channel_id"
    )
    line_login_channel_secret = fields.Char(
        string="LINE Login Channel Secret", config_parameter="line.login_channel_secret"
    )
