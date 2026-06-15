# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import ast
import json
import traceback

from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request


class WebhookController(http.Controller):
    def _call_function_api(self, model, vals, function):
        """
        This function will call the function from webhook.utils
        Can be hook to add something before or after the function
        """
        return getattr(request.env["webhook.utils"], function)(model, vals)

    def _create_api_logs(self, model, vals, function):
        ICP = request.env["ir.config_parameter"]
        rollback_state_failed = ICP.sudo().get_param("webhook.rollback_state_failed")
        rollback_except = ICP.sudo().get_param("webhook.rollback_except")

        data_str = json.dumps(vals)
        state = "draft"
        res = {}

        try:
            res = self._call_function_api(model, vals, function)
            state = "done" if res.get("is_success") else "failed"
            # Not success, rollback all data (if config in system parameter)
            if not res.get("is_success") and rollback_state_failed:
                request.env.cr.rollback()
        except Exception:
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
            log = request.env["api.log"].create(
                {
                    "model": model,
                    "route": f"/api/{function}",
                    "function_name": function,
                    "state": state,
                }
            )
            log._save_payload(data_str, json.dumps(res, ensure_ascii=False))
        self._link_callback_url(model, vals, res, log)
        return res

    def _link_callback_url(self, model, vals, res, log=None):
        """Store callback_url on api.log linked to the created/updated record.
        This enables outbound webhooks to find the correct endpoint per record.
        """
        callback_url = vals.get("callback_url")
        if not callback_url:
            return
        res_id = None
        result = res.get("result")
        if isinstance(result, dict):
            res_id = result.get("id")
        if not res_id:
            return
        linkage = {"res_model": model, "res_id": res_id, "callback_url": callback_url}
        if log:
            log.write(linkage)
        else:
            request.env["api.log"].create(
                {
                    "model": model,
                    "log_type": "receive",
                    "state": "done" if res.get("is_success") else "failed",
                    **linkage,
                }
            )
        rec = request.env[model].sudo().browse(res_id)
        if "callback_url" in rec._fields:
            rec.with_context(_webhook_outbound_dispatching=True).write(
                {"callback_url": callback_url}
            )

    def _set_create_logs(self, param, vals):
        ICP = request.env["ir.config_parameter"]
        is_create_log = ICP.sudo().get_param(param)
        # convert str to bool
        is_create_log = ast.literal_eval(is_create_log.capitalize())
        vals.update({"is_create_log": is_create_log})

    def update_session_auth(self):
        # Check session first. if no session, use API Key
        if request.session.uid:
            request.uid = request.session.uid
        else:
            # NOTE: header send only x-api-key instead of Authorization: Bearer <key>
            # If it not standard, i will remove later
            access_token = request.httprequest.headers.get("x-api-key")
            if access_token:
                user_id = request.env["res.users.apikeys"]._check_credentials(
                    scope="rpc", key=access_token
                )
                if not user_id:
                    raise BadRequest("Access token invalid")
                request.uid = user_id
                return
            request.env["ir.http"]._auth_method_bearer()

    @http.route("/api/create_data", type="json", auth="none")
    def create_data(self, model, vals):
        self.update_session_auth()
        self._set_create_logs("webhook.create_data_log", vals)
        res = self._create_api_logs(model, vals, "create_data")
        return res

    @http.route("/api/update_data", type="json", auth="none")
    def update_data(self, model, vals):
        self.update_session_auth()
        self._set_create_logs("webhook.update_data_log", vals)
        res = self._create_api_logs(model, vals, "update_data")
        return res

    @http.route("/api/create_update_data", type="json", auth="none")
    def create_update_data(self, model, vals):
        self.update_session_auth()
        self._set_create_logs("webhook.create_update_data_log", vals)
        res = self._create_api_logs(model, vals, "create_update_data")
        return res

    @http.route("/api/search_data", type="json", auth="none")
    def search_data(self, model, vals):
        self.update_session_auth()
        self._set_create_logs("webhook.search_data_log", vals)
        res = self._create_api_logs(model, vals, "search_data")
        return res

    @http.route("/api/call_function", type="json", auth="none")
    def call_function(self, model, vals):
        self.update_session_auth()
        self._set_create_logs("webhook.call_function_log", vals)
        res = self._create_api_logs(model, vals, "call_function")
        return res
