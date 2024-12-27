# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import secrets
import string

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    line_access_token = fields.Char(
        string="LINE Access Token", help="Access token for LINE Messaging API."
    )
    chat_uuid = fields.Char(string="Chat UUID", help="UUID for the chat session.")

    def get_line_access_token(self):
        ICP = self.env["ir.config_parameter"].sudo()
        line_login_url = ICP.get_param("line.url.login")
        line_login_channel_id = ICP.get_param("line.login_channel_id")
        base_url = ICP.get_param("web.base.url")

        # Generate a random alphanumeric string for the state parameter
        state = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
        )

        # Include the Partner ID in the state parameter
        state_with_partner_id = f"{state}:{self.id}"

        url = (
            f"{line_login_url}?response_type=code"
            f"&client_id={line_login_channel_id}"
            f"&redirect_uri={base_url}/line/authentication"
            f"&state={state_with_partner_id}"
            f"&bot_prompt=aggressive"
            f"&scope=openid%20email"
        )
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
