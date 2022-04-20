# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import http
from odoo.http import request


class WebhookController(http.Controller):
    @http.route("/api/create_data", type="json", auth="none")
    def create_data(self, model, vals):
        # Authentication
        head = request.httprequest.headers
        request.session.authenticate(head["db"], head["login"], head["password"])
        # Create Data
        res = request.env["webhook.utils"].create_data(model, vals)
        return res

    @http.route("/api/create_update_data", type="json", auth="none")
    def create_update_data(self, model, vals):
        head = request.httprequest.headers
        request.session.authenticate(head["db"], head["login"], head["password"])
        # Create/Update Data
        res = request.env["webhook.utils"].create_update_data(model, vals)
        return res
