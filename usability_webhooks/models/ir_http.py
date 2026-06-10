# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re

import werkzeug.exceptions

from odoo import _, models
from odoo.exceptions import AccessDenied
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_bearer(cls):
        headers = request.httprequest.headers

        def get_http_authorization_bearer_token():
            header = headers.get("Authorization")
            if header:
                m = re.match(r"^bearer\s+(.+)$", header, re.IGNORECASE)
                if m:
                    return m.group(1)
            return None

        def check_sec_headers():
            return (
                headers.get("Sec-Fetch-Dest") == "document"
                and headers.get("Sec-Fetch-Mode") == "navigate"
                and headers.get("Sec-Fetch-Site") in ("none", "same-origin")
                and headers.get("Sec-Fetch-User") == "?1"
            )

        token = get_http_authorization_bearer_token()
        if token:
            uid = request.env["res.users.apikeys"]._check_credentials(
                scope="rpc", key=token
            )
            if not uid:
                raise werkzeug.exceptions.Unauthorized("Invalid apikey")
            if request.uid and request.uid != uid:
                raise AccessDenied(_("Session user does not match the used apikey"))
            request.uid = uid
            return
        elif not request.uid:
            raise werkzeug.exceptions.Unauthorized(
                'User not authenticated, use the "Authorization" header'
            )
        elif not check_sec_headers():
            raise AccessDenied(
                _('Missing "Authorization" or Sec-headers for interactive usage')
            )
        cls._auth_method_user()
