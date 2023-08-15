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
        try:
            res = request.env["webhook.utils"].create_data(model, vals)
            state = "done" if res["is_success"] else "failed"
            data_dict.update({"result": res, "state": state})
        except Exception as e:
            res = {
                "is_success": False,
                "messages": e,
            }
            data_dict.update({"result": res, "state": "failed"})
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
        try:
            res = request.env["webhook.utils"].create_update_data(model, vals)
            state = "done" if res["is_success"] else "failed"
            data_dict.update({"result": res, "state": state})
        except Exception as e:
            res = {
                "is_success": False,
                "messages": e,
            }
            data_dict.update({"result": res, "state": "failed"})
        request.env["api.log"].create(data_dict)
        return res
