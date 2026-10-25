# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import HttpCase, tagged
from odoo.tools import mute_logger

CONTROLLER_LOGGER = "odoo.addons.usability_webhooks.controllers.main"


@tagged("post_install", "-at_install")
class TestWebhookController(HttpCase):
    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"]
        self.test_log = self.env["api.log"].create({"function_name": "Http Test"})
        # The database may already have logs of earlier calls
        self.last_log_id = self.test_log.id
        self.authenticate("admin", "admin")

    def _post_api(self, route, model, vals, headers=None):
        response = self.url_open(
            f"/api/{route}",
            data=json.dumps({"params": {"model": model, "vals": vals}}),
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        response.raise_for_status()
        return response.json()

    def _call_api(self, route, model, vals, headers=None):
        return self._post_api(route, model, vals, headers=headers)["result"]

    def _search_vals(self):
        return {
            "payload": {
                "search_field": ["function_name"],
                "search_domain": f"[('id', '=', {self.test_log.id})]",
            }
        }

    def _search_logs(self, route="/api/search_data"):
        return self.env["api.log"].search(
            [("route", "=", route), ("id", ">", self.last_log_id)]
        )

    def test_01_search_data_without_log(self):
        self.ICP.set_bool("webhook.search_data_log", False)
        res = self._call_api("search_data", "api.log", self._search_vals())
        self.assertTrue(res["is_success"])
        self.assertEqual(res["result"][0]["function_name"], "Http Test")
        self.assertFalse(self._search_logs())

    def test_02_search_data_with_log(self):
        self.ICP.set_bool("webhook.search_data_log", True)
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
        log = self._search_logs()
        self.assertEqual(len(log), 1)
        self.assertEqual(log.state, "done")
        self.assertEqual(json.loads(log.data_preview)["payload"], vals["payload"])

    @mute_logger(CONTROLLER_LOGGER)
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
        self.ICP.set_bool("webhook.create_data_log", False)
        vals = {"payload": {"function_name": "Http Create"}}
        res = self._call_api("create_data", "api.log", vals)
        self.assertTrue(res["is_success"], res.get("messages"))
        log = self.env["api.log"].browse(res["result"]["id"])
        self.assertEqual(log.function_name, "Http Create")

    def test_05_log_keeps_original_request(self):
        """Request is logged as received, even if the call changes the payload"""
        self.ICP.set_bool("webhook.search_data_log", True)
        vals = self._search_vals()

        def mutate_payload(utils, model, vals):
            vals["payload"]["search_field"].append("changed")
            return []

        Utils = type(self.env["webhook.utils"])
        with patch.object(Utils, "_common_search_data", mutate_payload):
            self._call_api("search_data", "api.log", vals)
        log = self._search_logs()
        self.assertEqual(json.loads(log.data_preview)["payload"], vals["payload"])

    def test_06_api_key_authentication(self):
        """Without a session, an API key authenticates the call"""
        self.ICP.set_bool("webhook.search_data_log", False)
        api_key = (
            self.env["res.users.apikeys"]
            .with_user(self.env.ref("base.user_admin"))
            ._generate("rpc", "webhook", fields.Datetime.now() + timedelta(days=1))
        )
        self.logout()
        for headers in (
            {"Authorization": f"Bearer {api_key}"},
            {"x-api-key": api_key},
        ):
            res = self._call_api("search_data", "api.log", self._search_vals(), headers)
            self.assertTrue(res["is_success"])
        for headers in ({"Authorization": "Bearer wrong-key"}, {}):
            with mute_logger("odoo.http"):
                res = self._post_api(
                    "search_data", "api.log", self._search_vals(), headers
                )
            self.assertIn("Unauthorized", res["error"]["data"]["name"])

    def test_07_update_data_links_callback_url(self):
        """update_data returns a list of ids: callback URL is still linked"""
        self.ICP.set_bool("webhook.update_data_log", True)
        vals = {
            "search_key": {"function_name": "Http Test"},
            "callback_url": "https://caller.example.com/callback",
            "payload": {"function_name": "Linked"},
        }
        res = self._call_api("update_data", "api.log", vals)
        self.assertTrue(res["is_success"], res.get("messages"))
        log = self._search_logs("/api/update_data")
        self.assertEqual(log.res_model, "api.log")
        self.assertEqual(log.res_id, self.test_log.id)
        self.assertEqual(log.callback_url, vals["callback_url"])
        # Request logs do not create followers or tracking messages
        self.assertFalse(log.message_follower_ids)
