# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import json
import logging
import re
import traceback

from werkzeug.exceptions import Unauthorized

from odoo import http
from odoo.http import request
from odoo.tools import json_default

_logger = logging.getLogger(__name__)


class WebhookController(http.Controller):
    def _call_function_api(self, model, vals, function):
        """
        This function will call the function from webhook.utils
        Can be hook to add something before or after the function
        """
        return getattr(request.env["webhook.utils"], function)(model, vals)

    def _create_api_logs(self, model, vals, function):
        ICP = request.env["ir.config_parameter"].sudo()
        rollback_state_failed = ICP.get_bool("webhook.rollback_state_failed")
        rollback_except = ICP.get_bool("webhook.rollback_except")

        # Dump before the call (payload may change), only when log is needed
        data_str = json.dumps(vals) if vals.get("is_create_log") else ""
        state = "draft"
        res = {}

        try:
            res = self._call_function_api(model, vals, function)
            state = "done" if res.get("is_success") else "failed"
            # Not success, rollback all data (if config in system parameter)
            if not res.get("is_success") and rollback_state_failed:
                request.env.cr.rollback()
        except Exception:
            _logger.warning(
                "Webhook /api/%s failed on %s", function, model, exc_info=True
            )
            res = {
                "is_success": False,
                "messages": traceback.format_exc(),
            }
            state = "failed"
            # Error from odoo exception,
            # rollback all data (if config in system parameter)
            if rollback_except:
                request.env.cr.rollback()

        log = None
        if vals.get("is_create_log"):
            log = (
                request.env["api.log"]
                .sudo()
                .with_context(tracking_disable=True)
                .create(
                    {
                        "model": model,
                        "route": f"/api/{function}",
                        "function_name": function,
                        "state": state,
                    }
                )
            )
            log._save_payload(
                data_str,
                json.dumps(res, ensure_ascii=False, default=json_default),
            )
        # Ids returned by call_function/search_data are not checked: never
        # link them, the callback URL is written as superuser
        if function in ("create_data", "update_data", "create_update_data"):
            self._link_callback_url(model, vals, res, log)
        return res

    def _link_callback_url(self, model, vals, res, log=None):
        """Store callback_url on api.log linked to the created/updated record.
        This enables outbound webhooks to find the correct endpoint per record.
        """
        callback_url = vals.get("callback_url")
        result = res.get("result")
        if not callback_url or not isinstance(result, dict):
            return
        # create_data returns one id, update_data a list of ids
        res_ids = result.get("id")
        if not isinstance(res_ids, list):
            res_ids = [res_ids] if res_ids else []
        if not res_ids:
            return
        if len(res_ids) == 1:
            linkage = {
                "res_model": model,
                "res_id": res_ids[0],
                "callback_url": callback_url,
            }
            if log:
                log.write(linkage)
            else:
                request.env["api.log"].sudo().with_context(
                    tracking_disable=True
                ).create(
                    {
                        "model": model,
                        "log_type": "receive",
                        "state": "done" if res.get("is_success") else "failed",
                        **linkage,
                    }
                )
        records = request.env[model].sudo().browse(res_ids)
        if "callback_url" in records._fields:
            records.with_context(_webhook_outbound_dispatching=True).write(
                {"callback_url": callback_url}
            )

    def _set_create_logs(self, param, vals):
        is_create_log = request.env["ir.config_parameter"].sudo().get_bool(param, True)
        vals.update({"is_create_log": is_create_log})

    def _get_api_key(self):
        """API key sent as ``Authorization: Bearer <key>`` or ``x-api-key``"""
        headers = request.httprequest.headers
        match = re.match(
            r"^bearer\s+(.+)$", headers.get("Authorization", ""), re.IGNORECASE
        )
        return match.group(1) if match else headers.get("x-api-key")

    def update_session_auth(self):
        """Authenticate with the session, or else with an API key."""
        if request.session.uid:
            request.update_env(user=request.session.uid)
            return
        api_key = self._get_api_key()
        if not api_key:
            raise Unauthorized(
                "User not authenticated, use a session or an API Key with "
                "a Bearer Authorization header."
            )
        user_id = request.env["res.users.apikeys"]._check_credentials(
            scope="rpc", key=api_key
        )
        if not user_id:
            raise Unauthorized("Invalid API key")
        request.update_env(user=user_id)
        request.session.can_save = False  # stateless

    def _handle_api_call(self, model, vals, function):
        """Authenticate, then run ``function`` of webhook.utils and log it"""
        self.update_session_auth()
        self._set_create_logs(f"webhook.{function}_log", vals)
        return self._create_api_logs(model, vals, function)

    # auth="none" routes use a read-only cursor by default, which would fail on
    # first write then run the whole call again: all routes may write (api.log)
    @http.route("/api/create_data", type="jsonrpc", auth="none", readonly=False)
    def create_data(self, model, vals):
        return self._handle_api_call(model, vals, "create_data")

    @http.route("/api/update_data", type="jsonrpc", auth="none", readonly=False)
    def update_data(self, model, vals):
        return self._handle_api_call(model, vals, "update_data")

    @http.route("/api/create_update_data", type="jsonrpc", auth="none", readonly=False)
    def create_update_data(self, model, vals):
        return self._handle_api_call(model, vals, "create_update_data")

    @http.route("/api/search_data", type="jsonrpc", auth="none", readonly=False)
    def search_data(self, model, vals):
        return self._handle_api_call(model, vals, "search_data")

    @http.route("/api/call_function", type="jsonrpc", auth="none", readonly=False)
    def call_function(self, model, vals):
        return self._handle_api_call(model, vals, "call_function")
