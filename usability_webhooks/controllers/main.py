# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import json

from odoo import http
from odoo.http import request


class WebhookController(http.Controller):
    @http.route("/api/create_data", type="json", auth="none")
    def create_data(self, model, vals):
        # Authentication
        head = request.httprequest.headers
        request.session.authenticate(head["db"], head["login"], head["password"])
        # Add logs
        data_dict = {
            "data": json.dumps(vals),
            "model": model,
            "route": "/api/create_data",
        }
        # Create Data & Update logs
        ICP = request.env["ir.config_parameter"]
        rollback_state_failed = ICP.sudo().get_param("webhook.rollback_state_failed")
        rollback_except = ICP.sudo().get_param("webhook.rollback_except")
        try:
            res = request.env["webhook.utils"].create_data(model, vals)
            state = "done" if res["is_success"] else "failed"
            data_dict.update({"result": res, "state": state})
            # Not success, rollback all data (if config in system parameter)
            if not res["is_success"] and rollback_state_failed:
                request.env.cr.rollback()
        except Exception as e:
            res = {
                "is_success": False,
                "messages": e,
            }
            data_dict.update({"result": res, "state": "failed"})
            # Error from odoo exception, rollback all data (if config in system parameter)
            if rollback_except:
                request.env.cr.rollback()
        request.env["api.log"].create(data_dict)
        return res

    @http.route("/api/create_update_data", type="json", auth="none")
    def create_update_data(self, model, vals):
        head = request.httprequest.headers
        request.session.authenticate(head["db"], head["login"], head["password"])
        # Add logs
        data_dict = {
            "data": json.dumps(vals),
            "model": model,
            "route": "/api/create_update_data",
        }
        # Create/Update Data & Update logs
        ICP = request.env["ir.config_parameter"]
        rollback_state_failed = ICP.sudo().get_param("webhook.rollback_state_failed")
        rollback_except = ICP.sudo().get_param("webhook.rollback_except")
        try:
            res = request.env["webhook.utils"].create_update_data(model, vals)
            state = "done" if res["is_success"] else "failed"
            data_dict.update({"result": res, "state": state})
            # Not success, rollback all data (if config in system parameter)
            if not res["is_success"] and rollback_state_failed:
                request.env.cr.rollback()
        except Exception as e:
            res = {
                "is_success": False,
                "messages": e,
            }
            data_dict.update({"result": res, "state": "failed"})
            # Error from odoo exception, rollback all data (if config in system parameter)
            if rollback_except:
                request.env.cr.rollback()
        request.env["api.log"].create(data_dict)
        return res
