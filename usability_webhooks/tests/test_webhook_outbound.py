# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo_test_helper import FakeModelLoader

from odoo.tests.common import TransactionCase

STATIC_URL = "https://test.example.com/webhook"
CALLBACK_URL = "https://caller.example.com/callback"
REQUESTS_PATH = "requests.post"


class TestWebhookOutbound(TransactionCase):
    def setUp(self):
        super().setUp()
        self.loader = FakeModelLoader(self.env, self.__module__)
        self.loader.backup_registry()
        from .outbound_tester import APILogOutboundTester

        self.loader.update_registry((APILogOutboundTester,))

        self.partner = self.env.ref("base.res_partner_2")
        self.usd = self.env.ref("base.USD")

        # ir.model entry for api.log (real model -> always exists)
        self.api_log_model_id = self.env["ir.model"].search([("model", "=", "api.log")])

        # Static-endpoint rule: fires when state -> done
        self.rule_static = (
            self.env["webhook.outbound.rule"]
            .sudo()
            .create(
                {
                    "name": "Test Static Rule",
                    "model_id": self.api_log_model_id.id,
                    "trigger_domain": "[('state', '=', 'done')]",
                    "endpoint_source": "static",
                    "endpoint_url": STATIC_URL,
                }
            )
        )

        # Record-callback rule: fires when state -> done, reads callback_url from record
        self.rule_callback = (
            self.env["webhook.outbound.rule"]
            .sudo()
            .create(
                {
                    "name": "Test Callback Rule",
                    "model_id": self.api_log_model_id.id,
                    "trigger_domain": "[('state', '=', 'done')]",
                    "endpoint_source": "record",
                }
            )
        )

    def tearDown(self):
        self.loader.restore_registry()
        super().tearDown()

    # ----- helpers -----

    def _new_log(self, state="draft", function_name="test"):
        return (
            self.env["api.log"]
            .sudo()
            .create(
                {"log_type": "receive", "state": state, "function_name": function_name}
            )
        )

    def _mock_ok_response(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "OK"
        resp.raise_for_status = MagicMock()
        return resp

    # ----- _build_record_payload tests -----

    def test_01_build_record_payload_plain(self):
        """Plain field list returns correct values."""
        utils = self.env["webhook.utils"]
        result = utils._build_record_payload(
            self.partner, ["name", "email", "is_company"]
        )
        self.assertEqual(result["name"], self.partner.name)
        self.assertEqual(result["email"], self.partner.email)
        self.assertEqual(result["is_company"], self.partner.is_company)

    def test_02_build_record_payload_m2o_subfields(self):
        """country_id{id,name,code} expands many2one to list-of-dict."""
        be = self.env.ref("base.be")
        self.partner.country_id = be
        utils = self.env["webhook.utils"]
        result = utils._build_record_payload(
            self.partner, ["name", "country_id{id,name,code}"]
        )
        self.assertIn("country_id", result)
        # many2one expands to list (consistent with search_data behaviour)
        country_data = result["country_id"]
        self.assertIsInstance(country_data, list)
        self.assertEqual(len(country_data), 1)
        self.assertEqual(country_data[0]["id"], be.id)
        self.assertEqual(country_data[0]["name"], be.name)
        self.assertEqual(country_data[0]["code"], be.code)

    def test_03_build_record_payload_empty_spec(self):
        """Empty fields_spec returns dict with id only."""
        utils = self.env["webhook.utils"]
        result = utils._build_record_payload(self.partner, [])
        self.assertEqual(result, {"id": self.partner.id})

    # ----- outbound dispatch tests -----

    def test_04_outbound_static_trigger_and_log(self):
        """write() matching trigger_domain -> POST
        to static URL + api.log send created."""
        # Disable callback rule so only static rule fires
        self.rule_callback.active = False
        log = self._new_log(state="draft")

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            log.write({"state": "done"})

        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        self.assertEqual(call_url, STATIC_URL)

        # api.log "send" entry created with state=done
        send_log = (
            self.env["api.log"]
            .sudo()
            .search([("log_type", "=", "send"), ("route", "=", STATIC_URL)], limit=1)
        )
        self.assertTrue(send_log)
        self.assertEqual(send_log.state, "done")

        self.rule_callback.active = True

    def test_05_outbound_no_trigger_wrong_state(self):
        """write() with state != trigger_value -> no HTTP call."""
        self.rule_callback.active = False
        log = self._new_log(state="draft")

        with patch(REQUESTS_PATH) as mock_post:
            log.write({"state": "failed"})  # rule expects "done"

        mock_post.assert_not_called()
        self.rule_callback.active = True

    def test_06_outbound_no_trigger_irrelevant_field(self):
        """write() on field not in domain -> no HTTP call."""
        self.rule_callback.active = False
        log = self._new_log(state="draft")

        with patch(REQUESTS_PATH) as mock_post:
            log.write({"function_name": "irrelevant"})

        mock_post.assert_not_called()
        self.rule_callback.active = True

    def test_07_outbound_complex_domain(self):
        """Two-condition domain: both must match to fire."""
        # domain: state=done AND data_size > 0
        rule = (
            self.env["webhook.outbound.rule"]
            .sudo()
            .create(
                {
                    "name": "Complex Domain Rule",
                    "model_id": self.api_log_model_id.id,
                    "trigger_domain": "[('state', '=', 'done'), ('data_size', '>', 0)]",
                    "endpoint_source": "static",
                    "endpoint_url": STATIC_URL,
                }
            )
        )
        self.rule_static.active = False
        self.rule_callback.active = False

        # data_size = 0 -> should NOT fire
        log_small = self._new_log(state="draft")
        with patch(REQUESTS_PATH) as mock_post:
            log_small.write({"state": "done"})
        mock_post.assert_not_called()

        # data_size > 0 -> SHOULD fire
        log_big = self._new_log(state="draft")
        log_big.data_size = 999
        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            log_big.write({"state": "done"})
        mock_post.assert_called_once()

        rule.unlink()
        self.rule_static.active = True
        self.rule_callback.active = True

    def test_08_outbound_callback_url_on_record(self):
        """endpoint_source=record:
        callback_url on record (fast path) -> POST to that URL."""
        self.rule_static.active = False
        log = self._new_log(state="draft")

        # Simulate controller writing callback_url directly onto the record
        log.with_context(_webhook_outbound_dispatching=True).write(
            {"callback_url": CALLBACK_URL}
        )

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            log.write({"state": "done"})

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], CALLBACK_URL)

        self.rule_static.active = True

    def test_08b_outbound_callback_url_fallback_from_log(self):
        """endpoint_source=record,
        record.callback_url empty -> fallback to api.log search."""
        self.rule_static.active = False
        log = self._new_log(state="draft")

        # Simulate controller storing callback_url on a linked api.log receive entry
        self.env["api.log"].sudo().create(
            {
                "model": "api.log",
                "res_model": "api.log",
                "res_id": log.id,
                "log_type": "receive",
                "callback_url": CALLBACK_URL,
                "state": "done",
            }
        )

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            log.write({"state": "done"})

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], CALLBACK_URL)

        self.rule_static.active = True

    def test_09_outbound_http_failure_logs_failed(self):
        """HTTP exception -> api.log send entry with state=failed."""
        self.rule_callback.active = False
        log = self._new_log(state="draft")

        with patch(REQUESTS_PATH, side_effect=Exception("Connection refused")):
            log.write({"state": "done"})

        failed_log = (
            self.env["api.log"]
            .sudo()
            .search(
                [
                    ("log_type", "=", "send"),
                    ("route", "=", STATIC_URL),
                    ("state", "=", "failed"),
                ],
                limit=1,
            )
        )
        self.assertTrue(failed_log)

        self.rule_callback.active = True

    def test_10_outbound_no_url_no_crash(self):
        """endpoint_source=record
        but no callback_url in api.log -> warning, no crash."""
        self.rule_static.active = False
        log = self._new_log(state="draft")
        # No api.log entry linking this record -> _resolve_endpoint returns None

        with patch(REQUESTS_PATH) as mock_post:
            log.write({"state": "done"})  # must not raise

        mock_post.assert_not_called()
        self.rule_static.active = True

    def test_11_invalid_domain_no_crash(self):
        """Invalid trigger_domain string -> warning logged, no exception."""
        rule = (
            self.env["webhook.outbound.rule"]
            .sudo()
            .create(
                {
                    "name": "Bad Domain Rule",
                    "model_id": self.api_log_model_id.id,
                    "trigger_domain": "NOT_VALID_DOMAIN",
                    "endpoint_source": "static",
                    "endpoint_url": STATIC_URL,
                }
            )
        )
        self.rule_static.active = False
        self.rule_callback.active = False
        log = self._new_log(state="draft")

        with patch(REQUESTS_PATH) as mock_post:
            log.write({"state": "done"})  # must not raise

        mock_post.assert_not_called()

        rule.unlink()
        self.rule_static.active = True
        self.rule_callback.active = True

    def test_12_invalid_payload_fields_fallback(self):
        """Bad JSON in payload_fields -> payload falls back to id only."""
        self.rule_callback.active = False
        self.rule_static.payload_fields = "NOT_VALID_JSON"
        log = self._new_log(state="draft")

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            log.write({"state": "done"})

        mock_post.assert_called_once()
        import json

        sent_payload = json.loads(mock_post.call_args[1]["data"].decode())
        self.assertIn("id", sent_payload)
        self.assertEqual(sent_payload["id"], log.id)

        self.rule_static.payload_fields = False
        self.rule_callback.active = True
