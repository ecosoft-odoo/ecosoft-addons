# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LineWebhook(http.Controller):
    @http.route("/line/authentication", type="http", auth="public")
    def line_oauth2callback(self, **kw):
        """This route/function is called by LINE
        when user Accept/Refuse the consent of LINE"""
        base_url = request.httprequest.url_root.strip("/")

        if kw.get("code"):
            # Get ID Token from LINE
            LineService = request.env["line.service"]
            id_token = LineService.with_context(base_url=base_url)._get_line_tokens(
                kw["code"]
            )
            # Set token to partner
            LineService._set_line_partner_access_token(kw.get("state", False), id_token)
            return request.redirect(base_url + "/web")
        # else:
        #     return request.redirect("%s%s" % (url_return, "?error=Unknown_error"))
        # TODO: Handle error
        return "Something went wrong"
