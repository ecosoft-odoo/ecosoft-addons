# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

# import jwt
import requests

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

LINE_TOKEN_ENDPOINT = "https://api.line.me/oauth2/v2.1/token"
LINE_TOKEN_VERIFY_ENDPOINT = "https://api.line.me/oauth2/v2.1/verify"


class LINEService(models.AbstractModel):
    _name = "line.service"
    _description = "LINE Service"

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

    def _search_line_partner_token(self, access_token):
        partner = self.env["res.partner"].search(
            [("line_access_token", "=", access_token)], limit=1
        )
        if not partner:
            raise UserError(_("The partner is not found"))
        return partner

    @api.model
    def _do_request(
        self, uri, params=None, headers=None, method="POST", timeout=TIMEOUT
    ):
        """Execute the request to LINE API.
        Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param uri : the url to contact
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param method : the method to use to make the request
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        _logger.debug(
            "Uri: %s - Type : %s - Headers: %s - Params : %s !",
            uri,
            method,
            headers,
            params,
        )
        ask_time = fields.Datetime.now()
        try:
            if method.upper() in ("GET", "DELETE"):
                res = requests.request(
                    method.lower(), uri, params=params, timeout=timeout
                )
            elif method.upper() in ("POST", "PATCH", "PUT"):
                res = requests.request(
                    method.lower(), uri, data=params, headers=headers, timeout=timeout
                )
            else:
                raise Exception(
                    _(
                        "Method not supported [%s] not in "
                        "[GET, POST, PUT, PATCH or DELETE]!"
                    )
                    % (method)
                )
            res.raise_for_status()
            status = res.status_code

            if int(status) == 204:  # Page not found, no response
                response = False
            else:
                response = res.json()

            try:
                ask_time = datetime.strptime(
                    res.headers.get("date", ""), "%a, %d %b %Y %H:%M:%S %Z"
                )
            except ValueError:
                _logger.exception("ValueError: %s", res.headers.get("date", ""))
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad line request : %s !", error.response.content)
                raise error
        return (status, response, ask_time)

    def _create_channel_discuss(self, partner, partner_permission_ids, MailChannel):
        all_partners = partner_permission_ids + partner
        mail_channel = MailChannel.create(
            {
                "name": "LINE: " + partner.name,
                "public": "private",
                "channel_partner_ids": [
                    Command.set(partner.id) for partner in all_partners
                ],
                "line_connect": True,
            }
        )
        # Update partner primary channel
        mail_channel.channel_last_seen_partner_ids.filtered(
            lambda cp: cp.partner_id == partner
        ).write({"use_line": True})
        return mail_channel

    @api.model
    def handle_message_received_event(self, events, channel_access_token):
        self = self.sudo()
        # configuration = Configuration(access_token=channel_access_token)
        message_list = []
        # Use public user to create discuss channel
        public_user = self.env.ref("base.public_user")
        MailChannel = self.env["mail.channel"].with_user(public_user.id).sudo()

        # Search all users who have permission group base.account_invoice_user
        line_operator_group = self.env.ref("line_chatbot.group_line_operater")
        users_with_permission = self.env["res.users"].search(
            [("groups_id", "in", line_operator_group.id)]
        )
        partner_permission_ids = users_with_permission.mapped("partner_id")

        for event in events:
            user_access_token = event.source.user_id

            if event.message.type == "image":
                # TODO: https://developers.line.biz/en/reference/messaging-api/#get-image-or-video-preview
                # Preview image or video
                message = event.message.id  # Image ID
            elif event.message.type == "sticker":
                # TODO: https://developers.line.biz/en/reference/messaging-api/#sticker-message
                # How to show sticker in Odoo or not need?
                # Format: packageId:stickerId
                message = f"{event.message.package_id}:{event.message.sticker_id}"
            elif event.message.type == "location":
                # How to show location in Odoo or not need?
                # Format: latitude:longitude:address
                message = f"{event.message.latitude}:{event.message.longitude}:{event.message.address}"
            else:
                message = event.message.text

            partner = self._search_line_partner_token(user_access_token)

            # Add log message
            message_list.append(
                {
                    "partner_id": partner.id,
                    "log_type": "receive",
                    "message_type": event.message.type,
                    "message": message,
                }
            )
            # Create discuss channel if not exist
            mail_channel = False
            if not partner.chat_uuid:
                mail_channel = self._create_channel_discuss(
                    partner, partner_permission_ids, MailChannel
                )
                # Update UUID TO partner 1:1 chat
                partner.write({"chat_uuid": mail_channel.uuid})
                notification = _(
                    '<div class="o_mail_notification">joined the channel</div>'
                )
                # Message Join Channel
                mail_channel.message_post(
                    body=notification,
                    message_type="notification",
                    author_id=partner.id,
                    subtype_xmlid="mail.mt_comment",
                    notify_by_email=False,
                )

            # Already have channel, search by UUID
            if not mail_channel:
                mail_channel = MailChannel.search([("uuid", "=", partner.chat_uuid)])

            # Check if partner permission is not in channel, add partner to channel
            missing_partners = partner_permission_ids - mail_channel.channel_partner_ids
            if missing_partners:
                mail_channel.write(
                    {
                        "channel_partner_ids": [
                            (4, partner.id) for partner in missing_partners
                        ]
                    }
                )

            # Send message to discuss channel
            mail_channel.message_post(
                body=message,
                message_type="notification",
                author_id=partner.id,
                subtype_xmlid="mail.mt_comment",
                notify_by_email=False,
            )

            # Send message to LINE (Reply message)
            # if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            #     with ApiClient(configuration) as api_client:
            #         line_bot_api = MessagingApi(api_client)
            #         line_bot_api.reply_message_with_http_info(
            #             ReplyMessageRequest(
            #                 reply_token=event.reply_token,
            #                 messages=[TextMessage(text=event.message.text)]
            #             )
            #         )

        message_log = self.env["line.message"].create(message_list)
        return message_log
