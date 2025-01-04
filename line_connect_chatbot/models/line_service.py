# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

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
    _inherit = "line.service"

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

        for event in events:
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
                message = (
                    f"{event.message.latitude}:{event.message.longitude}:"
                    f"{event.message.address}"
                )
            else:
                message = event.message.text

            partner = self._search_line_partner_token(event, configuration, message)

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
