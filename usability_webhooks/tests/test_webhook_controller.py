# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestWebhookController(HttpCase):
    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"]
        self.test_log = self.env["api.log"].create({"function_name": "Http Test"})
        self.authenticate("admin", "admin")

    def _call_api(self, route, model, vals):
        response = self.url_open(
            f"/api/{route}",
            data=json.dumps({"params": {"model": model, "vals": vals}}),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()["result"]

    def _search_vals(self):
        return {
            "payload": {
                "search_field": ["function_name"],
                "search_domain": f"[('id', '=', {self.test_log.id})]",
            }
        }

    def _count_logs(self):
        return self.env["api.log"].search_count([("route", "=", "/api/search_data")])

    def test_01_search_data_without_log(self):
        self.ICP.set_param("webhook.search_data_log", "False")
        res = self._call_api("search_data", "api.log", self._search_vals())
        self.assertTrue(res["is_success"])
        self.assertEqual(res["result"][0]["function_name"], "Http Test")
        self.assertEqual(self._count_logs(), 0)

    def test_02_search_data_with_log(self):
        self.ICP.set_param("webhook.search_data_log", "True")
        vals = self._search_vals()
        Utils = type(self.env["webhook.utils"])
        with patch.object(
            Utils,
            "_common_search_data",
            autospec=True,
            side_effect=Utils._common_search_data,
        ) as search:
            self._call_api("search_data", "api.log", vals)
        # Run once, no retry after a read-only cursor
        self.assertEqual(search.call_count, 1)
        log = self.env["api.log"].search([("route", "=", "/api/search_data")])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.state, "done")
        self.assertEqual(json.loads(log.data_preview)["payload"], vals["payload"])

    def test_03_call_function_private_method_refused(self):
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {"method": "_write", "parameter": {"vals": {"route": "x"}}},
        }
        res = self._call_api("call_function", "api.log", vals)
        self.assertFalse(res["is_success"])
        self.assertIn("AccessError", res["messages"])
        self.assertFalse(self.test_log.route)

    def test_04_create_data_without_log(self):
        """Write routes must run on a read/write cursor (auth='none' default is ro)"""
        self.ICP.set_param("webhook.create_data_log", "False")
        vals = {"payload": {"function_name": "Http Create"}}
        res = self._call_api("create_data", "api.log", vals)
        self.assertTrue(res["is_success"], res.get("messages"))
        log = self.env["api.log"].browse(res["result"]["id"])
        self.assertEqual(log.function_name, "Http Create")

    def test_05_log_keeps_original_request(self):
        """Request is logged as received, even if the call changes the payload"""
        self.ICP.set_param("webhook.search_data_log", "True")
        vals = self._search_vals()

        def mutate_payload(utils, model, vals):
            vals["payload"]["search_field"].append("changed")
            return []

        Utils = type(self.env["webhook.utils"])
        with patch.object(Utils, "_common_search_data", mutate_payload):
            self._call_api("search_data", "api.log", vals)
        log = self.env["api.log"].search([("route", "=", "/api/search_data")])
        self.assertEqual(json.loads(log.data_preview)["payload"], vals["payload"])
