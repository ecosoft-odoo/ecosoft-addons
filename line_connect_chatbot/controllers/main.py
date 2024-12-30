# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookParser

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LineWebhook(http.Controller):
    @http.route("/line/webhook", type="json", auth="none")
    def line_webhook(self):
        # Get channel secret and access token from Odoo configuration parameters
        ICP = request.env["ir.config_parameter"].sudo()
        channel_secret = ICP.get_param("line.channel_secret")
        channel_access_token = ICP.get_param("line.channel_access_token")

        if not channel_secret or not channel_access_token:
            _logger.error("LINE channel secret or access token not configured.")
            return http.Response(status=500)

        parser = WebhookParser(channel_secret)

        signature = request.httprequest.headers.get("X-Line-Signature")
        body = request.httprequest.data.decode("utf-8")
        _logger.info("Request body: %s", body)

        # Parse webhook body
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            _logger.error(
                "Invalid signature. Check your channel secret and access token."
            )
            return http.Response(status=400)

        # Handle events
        request.env["line.service"].handle_message_received_event(
            events, channel_access_token
        )

        return "OK"
