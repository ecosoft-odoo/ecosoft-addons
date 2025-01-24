# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LineWebhook(http.Controller):
    @http.route("/line/webhook/approval", type="http", auth="none")
    def line_webhook_approval(self, **kwargs):
        base_url = request.httprequest.url_root.strip("/")
        if kwargs["code"] == "detail":
            # TODO: Redirect to document
            return request.redirect(base_url + "/web")
        request.env[kwargs["model"]].handle_approval_document(**kwargs)
        return "OK"
