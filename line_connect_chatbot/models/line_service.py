# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging

import requests
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

from odoo import Command, _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

LINE_TOKEN_ENDPOINT = "https://api.line.me/oauth2/v2.1/token"
LINE_TOKEN_VERIFY_ENDPOINT = "https://api.line.me/oauth2/v2.1/verify"


class LINEService(models.AbstractModel):
    _name = "line.service"
    _description = "Common function for LINE Service"

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

    def _call_get_line_image(self, uri, headers):
        res = requests.request("get", uri, headers=headers, timeout=10)
        res.raise_for_status()
        status = res.status_code
        if int(status) == 204:  # Page not found, no response
            response = False
        else:
            response = res.content
        return response

    def _get_message_image(self, event, partner, headers):
        url_line_image = (
            self.env["ir.config_parameter"].sudo().get_param("line.url.api.image")
        )
        LINE_IMAGE_PREVIEW_ENDPOINT = (
            f"{url_line_image}/message/{event.message.id}/content"
        )

        try:
            content = self._call_get_line_image(LINE_IMAGE_PREVIEW_ENDPOINT, headers)
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                content = ""
            else:
                _logger.exception("Bad line request : %s !", error.response.content)
                raise error

        # Call success, create attachment and add message with image
        message = ""
        if content:
            channel = self.env["mail.channel"].search(
                [("uuid", "=", partner.chat_uuid)]
            )
            attachment = self.env["ir.attachment"].create(
                {
                    "name": "LINE Image",
                    "datas": base64.b64encode(content),
                    "type": "binary",
                    "res_model": "mail.channel",
                    "res_id": channel.id,
                }
            )
            message = '<img src="/web/content/%s" alt="LINE Image"/>' % attachment.id
        return message

    def _get_domain_register_partner(self, value_register):
        """Can be override to add more domain"""
        return [("email", "=", value_register)]

    def _message_register_partner_connect_line(
        self, event, value_register, configuration
    ):
        domain_partner = self._get_domain_register_partner(value_register)
        partner = self.env["res.partner"].search(domain_partner, limit=1)

        # Check email in system, if not found, reply message LINE to user
        if not partner:
            self.message_line_reply(
                configuration,
                event.reply_token,
                "The partner is not found in System, "
                "please try again or contact admin.",
            )
        else:
            # Check if partner already registered, if not, register the partner
            if partner.line_access_token:
                self.message_line_reply(
                    configuration,
                    event.reply_token,
                    "The partner is already registered.",
                )
                partner = False  # Return False to skip message post
            else:
                partner.write({"line_access_token": event.source.user_id})
                self.message_line_reply(
                    configuration,
                    event.reply_token,
                    "Register the partner successfully.",
                )
        return partner, event.message.text  # Return original message

    def _message_received_partner_line(self, event, configuration, headers=None):
        partner = self.env["res.partner"].search(
            [("line_access_token", "=", event.source.user_id)], limit=1
        )
        # Send message before register email, return message error
        if not partner:
            self.message_line_reply(
                configuration,
                event.reply_token,
                "Please register your email to connect with LINE.",
            )
            return partner, event.message.text

        headers = headers or {}

        if event.message.type == "image":
            # Preview image or video
            message = self._get_message_image(event, partner, headers)
        elif event.message.type == "sticker":
            # TODO: https://developers.line.biz/en/reference/messaging-api/#sticker-message
            # How to show sticker in Odoo or not need?
            # Format: packageId:stickerId
            message = f"{event.message.package_id}:{event.message.sticker_id}"
        elif event.message.type == "location":
            # How to show location in Odoo or not need?
            # Format: latitude:longitude:address
            message = (
                f"{event.message.latitude}:{event.message.longitude}:"
                f"{event.message.address}"
            )
        else:
            message = event.message.text
        return partner, message

    @api.model
    def handle_message_received_event(self, events, channel_access_token):
        """
        Main function to handle message received from LINE. Steps:
        1. Check message,
            - if message is /register, register partner with email.
            - else, check partner from line_access_token.
                - if not found, return message to partner.
                - if found, check message type and create message.
        2. Create discuss channel if not exist.
        3. Send message to discuss channel.
        4. Create log message.
        """
        self = self.sudo()
        configuration = Configuration(access_token=channel_access_token)
        message_list = []
        # Use public user to create discuss channel
        public_user = self.env.ref("base.public_user")
        MailChannel = self.env["mail.channel"].with_user(public_user.id).sudo()

        # Search all users who have permission group base.account_invoice_user
        line_operator_group = self.env.ref("line_connect_chatbot.group_line_operater")
        users_with_permission = self.env["res.users"].search(
            [("groups_id", "in", line_operator_group.id)]
        )
        partner_permission_ids = users_with_permission.mapped("partner_id")

        # Headers for LINE API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel_access_token}",
        }

        for event in events:
            if event.message.type == "text" and event.message.text.startswith(
                "/register"
            ):
                # Register partner with email
                value_register = event.message.text.split(" ")[1]
                partner, message = self._message_register_partner_connect_line(
                    event, value_register, configuration
                )
            else:
                partner, message = self._message_received_partner_line(
                    event, configuration, headers
                )

            # No partner from 3 cases,
            # 1. Partner not found in system
            # 2. Partner already registered
            # 3. Partner not register email but send message
            if not partner:
                continue

            # Add log message
            message_list.append(
                {
                    "partner_id": partner.id,
                    "log_type": "receive",
                    "message_type": event.message.type,
                    "message": message,
                }
            )

            # Create discuss channel if not exist (Register first time)
            mail_channel = False
            if not partner.chat_uuid:
                mail_channel = self._create_channel_discuss(
                    partner, partner_permission_ids, MailChannel
                )
                # Update UUID to partner 1:1 chat
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
            # NOTE: Use for case remove channel, user will can't see channel in chat
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

        message_log = self.env["line.message"].create(message_list)
        return message_log

    @api.model
    def message_line_reply(self, configuration, reply_token, message):
        # Send message to LINE (Reply message)
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token, messages=[TextMessage(text=message)]
                )
            )

    @api.model
    def message_line_attachment(self, attachments, message_list=None):
        """Generate access token for attachment"""
        message_list = message_list or []
        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        attachments.generate_access_token()
        for attach in attachments:
            content_url = "{}/web/image/{}?access_token={}".format(
                web_base_url,
                attach.id,
                attach.access_token,
            )
            if attach.index_content == "image":
                message_list.append(
                    {
                        "type": "image",
                        "originalContentUrl": content_url,
                        "previewImageUrl": content_url,
                    }
                )
            # Send data with template file
            elif attach.mimetype == "application/pdf":
                # TODO: support only pdf, other file can't open
                message_list.append(
                    {
                        "type": "template",
                        "altText": attach.name,
                        "template": {
                            "type": "buttons",
                            "title": attach.name,
                            "text": attach.mimetype[:59],  # limit 60 char
                            "actions": [
                                {
                                    "type": "uri",
                                    "label": "Open file",
                                    "uri": content_url,
                                }
                            ],
                        },
                    }
                )
            else:
                raise UserError(
                    _("Only PDF and Image files are allowed as attachments.")
                )
        return message_list

    @api.model
    def message_line_push(self, message_list, partner_ids=None, broadcast=False):
        partner_ids = partner_ids or []
        if broadcast:
            _logger.info(f"Broadcast message to LINE with {message_list}")
            message_push = "broadcast"
            payload = {"messages": message_list}
        else:
            _logger.info(f"Send message to LINE with {message_list} to {partner_ids}")
            partners = self.env["res.partner"].browse(partner_ids)
            partner_line_access_token = partners.mapped("line_access_token")

            if not partner_line_access_token:
                raise UserError(_("No LINE access token found for the partner."))

            if len(partner_line_access_token) > 1:
                message_push = "multicast"  # 1:Many chat
            else:
                message_push = "push"  # 1:1 chat
                partner_line_access_token = partner_line_access_token[0]
            payload = {
                "to": partner_line_access_token,
                "messages": message_list,
            }

        get_param = self.env["ir.config_parameter"].sudo().get_param

        server_url = get_param("line.url.api")
        channel_access_token = get_param("line.channel_access_token")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel_access_token}",
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

        if broadcast:
            message_log = {
                "partner_id": False,
                "log_type": "send",
                "message_type": "text",
                "is_broadcast": True,
                "message": message_list,
                # broadcase return {} if success
                "state": "sent" if response == {} else "failed",
                "message_error": error_message,
            }
        else:
            message_log = [
                {
                    "partner_id": partners.id,  # TODO: Change to partner_ids
                    "log_type": "send",
                    "message_type": "text",  # TODO: Should support file or image type
                    "message": message_list,  # TODO: change list to message
                    "state": "sent" if response else "failed",
                    "message_error": error_message,
                }
                for partner in partners
            ]
        self.env["line.message"].sudo().create(message_log)
        return response
