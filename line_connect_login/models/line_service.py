# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

LINE_TOKEN_ENDPOINT = "https://api.line.me/oauth2/v2.1/token"
LINE_TOKEN_VERIFY_ENDPOINT = "https://api.line.me/oauth2/v2.1/verify"


class LINEService(models.AbstractModel):
    _inherit = "line.service"

    @api.model
    def _get_line_tokens(self, authorize_code):
        """Call LINE API to exchange authorization code against token,
        with POST request, to not be redirected."""
        get_param = self.env["ir.config_parameter"].sudo().get_param
        base_url = self._context.get("base_url") or self.env.user.get_base_url()

        grant_type = get_param("line.url.login.grant.type")
        line_login_channel_id = get_param("line.login_channel_id")
        line_login_channel_secret = get_param("line.login_channel_secret")

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": grant_type,
            "code": authorize_code,
            "redirect_uri": base_url + "/line/authentication",
            "client_id": line_login_channel_id,
            "client_secret": line_login_channel_secret,
        }

        try:
            dummy, response, dummy = self._do_request(
                LINE_TOKEN_ENDPOINT, params=data, headers=headers, method="POST"
            )
            id_token = response.get("id_token")
            return id_token
        except requests.HTTPError:
            error_msg = _(
                "Something went wrong during your token generation. "
                "Maybe your Authorization Code is invalid"
            )
            raise UserError(error_msg) from None

    def decode_id_token(self, id_token):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        line_login_channel_id = get_param("line.login_channel_id")
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "id_token": id_token,
            "client_id": line_login_channel_id,
        }
        # Decode the JWT token
        try:
            # NOTE: We can request to LINE to verify the token or decode it by ourselves
            dummy, decoded_token, dummy = self._do_request(
                LINE_TOKEN_VERIFY_ENDPOINT, params=data, headers=headers, method="POST"
            )
            # decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            return decoded_token
        # except jwt.ExpiredSignatureError:
        #     raise UserError(_("The token has expired"))
        # except jwt.InvalidTokenError:
        #     raise UserError(_("Invalid token"))
        except Exception as e:
            raise UserError(e) from e

    @api.model
    def _set_line_partner_access_token(self, state, id_token):
        """
        Set the access token to the partner.
        Format state is 'random_string:partner_id'
        """
        if not state:
            raise UserError(_("The state parameter is missing"))

        partner_id = state.split(":")[-1]
        partner = self.env["res.partner"].browse(int(partner_id))

        if not partner:
            raise UserError(_("The partner is not found"))

        # Decode the id_token and set the access token to the partner
        decoded_token = self.decode_id_token(id_token)

        # TODO: User should be able to set the token to the partner by themselves. How?
        partner.sudo().write({"line_access_token": decoded_token.get("sub", False)})
        return partner, decoded_token

    def _search_line_partner_token(self, event, configuration, message):
        partner = self.env["res.partner"].search(
            [("line_access_token", "=", event.source.user_id)], limit=1
        )
        if not partner:
            partner = self.env["res.partner"].search([("email", "=", message)], limit=1)
            # Check email from message, if not found, return message to user
            if not partner:
                self.message_line_reply(
                    configuration,
                    event.reply_token,
                    "The partner is not found in System, please contact admin.",
                )
            # Register the partner
            partner.write({"line_access_token": event.source.user_id})
            self.message_line_reply(
                configuration, event.reply_token, "Register the partner successfully."
            )
        return partner
