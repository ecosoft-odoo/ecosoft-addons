# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import json
import traceback

from odoo import http
from odoo.http import request


class WebhookController(http.Controller):
    def _create_api_logs(self, model, vals, function):
        # Add logs
        data_dict = {
            "data": json.dumps(vals),
            "model": model,
            "route": "/api/%(function)s" % {"function": function},
            "function_name": function,
        }

        ICP = request.env["ir.config_parameter"]
        rollback_state_failed = ICP.sudo().get_param("webhook.rollback_state_failed")
        rollback_except = ICP.sudo().get_param("webhook.rollback_except")
        try:
            res = getattr(request.env["webhook.utils"], function)(model, vals)
            state = "done" if res["is_success"] else "failed"
            data_dict.update({"result": res, "state": state})
            # Not success, rollback all data (if config in system parameter)
            if not res["is_success"] and rollback_state_failed:
                request.env.cr.rollback()
        except Exception:
            res = {
                "is_success": False,
                "messages": traceback.format_exc(),
            }
            data_dict.update({"result": res, "state": "failed"})
            # Error from odoo exception, rollback all data (if config in system parameter)
            if rollback_except:
                request.env.cr.rollback()
        request.env["api.log"].create(data_dict)
        return res

    @http.route("/api/create_data", type="json", auth="user")
    def create_data(self, model, vals):
        res = self._create_api_logs(model, vals, "create_data")
        return res

    @http.route("/api/update_data", type="json", auth="user")
    def update_data(self, model, vals):
        res = self._create_api_logs(model, vals, "update_data")
        return res

    @http.route("/api/create_update_data", type="json", auth="user")
    def create_update_data(self, model, vals):
        res = self._create_api_logs(model, vals, "create_update_data")
        return res

    @http.route("/api/search_data", type="json", auth="user")
    def search_data(self, model, vals):
        res = self._create_api_logs(model, vals, "search_data")
        return res

    @http.route("/api/call_function", type="json", auth="user")
    def call_function(self, model, vals):
        res = self._create_api_logs(model, vals, "call_function")
        return res
