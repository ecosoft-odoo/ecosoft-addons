# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers.discuss import DiscussController


class DiscussControllerLINE(DiscussController):
    def _get_allowed_message_post_params(self):
        """Add line_partner_ids to allowed message post params."""
        res = super()._get_allowed_message_post_params()
        res.add("line_partner_ids")
        return res

    @http.route("/mail/message/post", methods=["POST"], type="json", auth="public")
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        """Change message_type to 'line' if the channel is connected to LINE."""
        if thread_model == "mail.channel":
            channel = request.env["mail.channel"].browse(int(thread_id))
            if channel.line_connect:
                post_data["message_type"] = "line"
                # From chat, only send to partner that has use_line = True
                channel_partner = channel.channel_last_seen_partner_ids.filtered(
                    lambda x: x.use_line
                )
                post_data["line_partner_ids"] = channel_partner.partner_id.ids
                # Convert message to LINE format
                if post_data.get("body"):
                    message_list = [
                        {
                            "type": "text",
                            "text": post_data.get("body"),
                        }
                    ]
                else:
                    message_list = []

                if post_data.get("attachment_ids"):
                    attachments = request.env["ir.attachment"].browse(
                        post_data["attachment_ids"]
                    )
                    message_list = request.env["line.service"].message_line_attachment(
                        attachments, message_list
                    )
                post_data["body"] = message_list
        return super().mail_message_post(thread_model, thread_id, post_data, **kwargs)
