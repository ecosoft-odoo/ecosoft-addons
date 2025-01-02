# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BaseLineProcess(models.AbstractModel):
    _name = "base.line.process"
    _description = "Base function LINE Process"

    def message_line_push(self, message_list, partner_ids):
        _logger.info(f"Send message to LINE with{message_list} to {partner_ids}")
        partners = self.env["res.partner"].browse(partner_ids)
        partner_line_access_token = partners.mapped("line_access_token")

        if not partner_line_access_token:
            raise UserError(_("No LINE access token found for the partner."))

        if len(partner_line_access_token) > 1:
            message_push = "multicast"  # 1:Many chat
        else:
            message_push = "push"  # 1:1 chat
            partner_line_access_token = partner_line_access_token[0]

        get_param = self.env["ir.config_parameter"].sudo().get_param

        server_url = get_param("line.url.api")
        channel_access_token = get_param("line.channel_access_token")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel_access_token}",
        }
        payload = {
            "to": partner_line_access_token,
            "messages": message_list,
        }
        error_message = ""
        try:
            res = requests.post(
                url=f"{server_url}/message/{message_push}",
                headers=headers,
                json=payload,
                timeout=20,
            )

            res.raise_for_status()
            status = res.status_code

            if int(status) == 204:  # Page not found, no response
                response = False
            else:
                response = res.json()
        except Exception as e:
            _logger.error(f"Error: {e}")
            error_message = str(e)
            response = False

        self.env["line.message"].sudo().create(
            {
                "partner_id": partner.id,  # TODO: Change to partner_ids
                "log_type": "send",
                "message_type": "text",  # TODO: Should support file or image type
                "message": message_list,  # TODO: change list to message
                "state": "sent" if response else "failed",
                "message_error": error_message,
            }
            for partner in partners
        )

        return response
