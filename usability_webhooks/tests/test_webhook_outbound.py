# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user
from odoo.tools import mute_logger

from odoo.addons.usability_webhooks.controllers.main import WebhookController

from .common import WebhookTestCommon

STATIC_URL = "https://test.example.com/webhook"
CALLBACK_URL = "https://caller.example.com/callback"
REQUESTS_PATH = "requests.post"
SERVICE_LOGGER = "odoo.addons.usability_webhooks.models.webhook_outbound_service"
MIXIN_LOGGER = "odoo.addons.usability_webhooks.models.webhook_outbound_mixin"
RULE_LOGGER = "odoo.addons.usability_webhooks.models.webhook_outbound_rule"


class TestWebhookOutbound(WebhookTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Webhook Partner", "email": "webhook@example.com"}
        )
        cls.record_model_id = cls.env["ir.model"]._get_id("webhook.test.record")
        Rule = cls.env["webhook.outbound.rule"]
        # Static-endpoint rule: fires when state -> done
        cls.rule_static = Rule.create(
            {
                "name": "Test Static Rule",
                "model_id": cls.record_model_id,
                "trigger_domain": "[('state', '=', 'done')]",
                "endpoint_source": "static",
                "endpoint_url": STATIC_URL,
            }
        )
        # Record-callback rule: fires when state -> done, reads callback_url
        cls.rule_callback = Rule.create(
            {
                "name": "Test Callback Rule",
                "model_id": cls.record_model_id,
                "trigger_domain": "[('state', '=', 'done')]",
                "endpoint_source": "record",
                "allowed_callback_url": "https://caller.example.com",
            }
        )

    # ----- helpers -----

    def _new_record(self, state="draft", name="test", **vals):
        return self.Record.create({"state": state, "name": name, **vals})

    def _mock_ok_response(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "OK"
        resp.raise_for_status = MagicMock()
        resp.is_redirect = False
        return resp

    def _sent_payload(self, mock_post):
        return json.loads(mock_post.call_args[1]["data"].decode())

    def _send_logs(self, url=STATIC_URL):
        return self.env["api.log"].search(
            [("log_type", "=", "send"), ("route", "=", url)]
        )

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
        # many2one expands to list (consistent with search_data behaviour)
        self.assertEqual(
            result["country_id"], [{"id": be.id, "name": be.name, "code": be.code}]
        )

    def test_03_build_record_payload_empty_spec(self):
        """Empty fields_spec returns dict with id only."""
        utils = self.env["webhook.utils"]
        result = utils._build_record_payload(self.partner, [])
        self.assertEqual(result, {"id": self.partner.id})

    # ----- outbound dispatch tests -----

    def test_04_outbound_static_trigger_and_log(self):
        """write() matching trigger_domain -> POST
        to static URL + api.log send created."""
        self.rule_callback.active = False
        record = self._new_record()

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], STATIC_URL)
        send_log = self._send_logs()
        self.assertEqual(send_log.state, "done")
        self.assertEqual(send_log.res_model, "webhook.test.record")
        self.assertEqual(send_log.res_id, record.id)
        # Outbound logs do not create followers or tracking messages
        self.assertFalse(send_log.message_follower_ids)
        self.assertFalse(send_log.message_ids)

    def test_05_outbound_no_trigger_wrong_state(self):
        """write() with state != trigger_value -> no HTTP call."""
        self.rule_callback.active = False
        record = self._new_record()

        with patch(REQUESTS_PATH) as mock_post:
            record.write({"state": "failed"})  # rule expects "done"

        mock_post.assert_not_called()

    def test_06_outbound_no_trigger_irrelevant_field(self):
        """write() on field not in domain -> no HTTP call."""
        self.rule_callback.active = False
        record = self._new_record(state="done")

        with patch(REQUESTS_PATH) as mock_post:
            record.write({"name": "irrelevant"})

        mock_post.assert_not_called()

    def test_07_outbound_complex_domain(self):
        """Two-condition domain: both must match to fire, checked per record."""
        self.env["webhook.outbound.rule"].create(
            {
                "name": "Complex Domain Rule",
                "model_id": self.record_model_id,
                "trigger_domain": "[('state', '=', 'done'), ('amount', '>', 0)]",
                "endpoint_source": "static",
                "endpoint_url": STATIC_URL,
            }
        )
        (self.rule_static | self.rule_callback).active = False

        records = self._new_record(name="small") | self._new_record(
            name="big", amount=999
        )
        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            records.write({"state": "done"})

        # amount = 0 -> not sent, amount > 0 -> sent
        mock_post.assert_called_once()
        self.assertEqual(self._sent_payload(mock_post), {"id": records[1].id})

    def test_08_outbound_callback_url_on_record(self):
        """endpoint_source=record:
        callback_url on record (fast path) -> POST to that URL."""
        self.rule_static.active = False
        record = self._new_record()

        # Simulate controller writing callback_url directly onto the record
        record.with_context(_webhook_outbound_dispatching=True).write(
            {"callback_url": CALLBACK_URL}
        )

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], CALLBACK_URL)

    def test_08b_outbound_callback_url_fallback_from_log(self):
        """endpoint_source=record,
        record.callback_url empty -> fallback to api.log search."""
        self.rule_static.active = False
        record = self._new_record()

        # Simulate controller storing callback_url on a linked api.log receive entry
        self.env["api.log"].create(
            {
                "model": "webhook.test.record",
                "res_model": "webhook.test.record",
                "res_id": record.id,
                "log_type": "receive",
                "callback_url": CALLBACK_URL,
                "state": "done",
            }
        )

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args[0][0], CALLBACK_URL)

    def test_08c_callback_url_fallback_batched(self):
        """Logs of all written records are searched at once, the latest
        received log of each record gives its URL"""
        self.rule_static.active = False
        records = self._new_record() | self._new_record()
        self.env["api.log"].create(
            [
                {
                    "res_model": "webhook.test.record",
                    "res_id": rec.id,
                    "log_type": "receive",
                    "callback_url": f"{CALLBACK_URL}/{suffix}",
                }
                for rec, suffix in (
                    (records[0], "old"),
                    (records[0], "0"),
                    (records[1], "1"),
                )
            ]
        )
        Log = type(self.env["api.log"])
        with (
            patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post,
            patch.object(
                Log, "_read_group", autospec=True, side_effect=Log._read_group
            ) as read_group,
        ):
            records.write({"state": "done"})
        self.assertEqual(read_group.call_count, 1)
        self.assertEqual(
            sorted(call[0][0] for call in mock_post.call_args_list),
            [f"{CALLBACK_URL}/0", f"{CALLBACK_URL}/1"],
        )
        self.assertEqual(records.mapped("webhook_last_state"), ["done", "done"])

    @mute_logger(SERVICE_LOGGER)
    def test_09_outbound_http_failure_logs_failed(self):
        """HTTP exception -> api.log send entry with state=failed."""
        self.rule_callback.active = False
        record = self._new_record()

        with patch(REQUESTS_PATH, side_effect=Exception("Connection refused")):
            record.write({"state": "done"})

        self.assertEqual(self._send_logs().state, "failed")

    @mute_logger(MIXIN_LOGGER)
    def test_10_outbound_no_url_no_crash(self):
        """endpoint_source=record
        but no callback_url in api.log -> warning, no crash."""
        self.rule_static.active = False
        record = self._new_record()

        with patch(REQUESTS_PATH) as mock_post:
            record.write({"state": "done"})  # must not raise

        mock_post.assert_not_called()

    @mute_logger(RULE_LOGGER)
    def test_11_invalid_domain_no_crash(self):
        """Invalid trigger_domain string -> warning logged, no exception."""
        self.env["webhook.outbound.rule"].create(
            [
                {
                    "name": "Bad Domain Rule",
                    "model_id": self.record_model_id,
                    "trigger_domain": bad_domain,
                    "endpoint_source": "static",
                    "endpoint_url": STATIC_URL,
                }
                # Not Python, not a list, not a domain
                for bad_domain in ("NOT_VALID_DOMAIN", "None", "[('state', 'is', 1)]")
            ]
        )
        (self.rule_static | self.rule_callback).active = False
        record = self._new_record()

        with patch(REQUESTS_PATH) as mock_post:
            record.write({"state": "done"})  # must not raise

        mock_post.assert_not_called()

    @mute_logger(MIXIN_LOGGER)
    def test_12_invalid_payload_fields_fallback(self):
        """Bad JSON in payload_fields -> payload falls back to id only."""
        self.rule_callback.active = False
        self.rule_static.payload_fields = "NOT_VALID_JSON"
        record = self._new_record()

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        mock_post.assert_called_once()
        self.assertEqual(self._sent_payload(mock_post), {"id": record.id})

    def test_13_outbound_object_format_payload(self):
        """payload_fields as a JSON object -> static values kept as-is,
        {field.path} templates resolved recursively at any nesting level."""
        self.rule_callback.active = False
        self.rule_static.payload_fields = json.dumps(
            {
                "request_code": "{name}",
                "app": "MyApp",
                "data": {"id": "{id}", "state": "{state}"},
            }
        )
        record = self._new_record(name="SO001")

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        self.assertEqual(
            self._sent_payload(mock_post),
            {
                "request_code": "SO001",
                "app": "MyApp",
                "data": {"id": record.id, "state": "done"},
            },
        )

    @mute_logger(MIXIN_LOGGER)
    def test_13b_outbound_object_format_rejects_list(self):
        """payload_fields as a JSON array (old list format)
        is no longer supported -> payload falls back to id only."""
        self.rule_callback.active = False
        self.rule_static.payload_fields = json.dumps(["name", "state"])
        record = self._new_record()

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        self.assertEqual(self._sent_payload(mock_post), {"id": record.id})

    def test_14_resolve_field_value_scalar_and_related(self):
        """_resolve_field_value returns the raw value at the end of
        the path. A many2one field must be followed by an explicit
        subfield (e.g. '.name') to get anything other than the record
        itself. Plain strings pass through unchanged."""
        be = self.env.ref("base.be")
        self.partner.country_id = be
        mixin = self.Record

        self.assertEqual(
            mixin._resolve_field_value(self.partner, "{name}"), self.partner.name
        )
        self.assertEqual(
            mixin._resolve_field_value(self.partner, "{country_id.name}"), be.name
        )
        self.assertEqual(mixin._resolve_field_value(self.partner, "{country_id}"), be)
        self.assertEqual(
            mixin._resolve_field_value(self.partner, "static-value"), "static-value"
        )

    @mute_logger(MIXIN_LOGGER)
    def test_14c_resolve_field_value_multirecord_no_crash(self):
        """A {field.path} template that crosses a multi-record
        one2many/many2many field must not raise - Odoo's 'Expected
        singleton' error is caught and resolved to None instead of
        propagating and rolling back the triggering write()."""
        record = self._new_record(tag_ids=[(6, 0, (self.tag_a | self.tag_b).ids)])

        self.assertIsNone(self.Record._resolve_field_value(record, "{tag_ids.name}"))

    def test_14d_expand_one2many_list_of_object(self):
        """A one-item array value under a key matching a
        one2many/many2many field expands into one resolved object
        per related record, using that item as a per-record template."""
        record = self._new_record(
            line_ids=[(0, 0, {"name": "L1"}), (0, 0, {"name": "L2"})]
        )

        result = self.Record._resolve_dict_entry(
            record, "line_ids", [{"line_name": "{name}"}]
        )

        self.assertEqual(result, [{"line_name": "L1"}, {"line_name": "L2"}])

    def test_14e_non_relational_key_array_stays_literal(self):
        """A one-item array under a key that is NOT a one2many/many2many
        field on the record is left untouched (no false expansion)."""
        record = self._new_record()

        self.assertEqual(
            self.Record._resolve_dict_entry(record, "custom_tag", ["vip"]), ["vip"]
        )
        # 'name' is a real field but not one2many/many2many -> literal too
        self.assertEqual(
            self.Record._resolve_dict_entry(record, "name", ["static"]), ["static"]
        )

    @mute_logger(SERVICE_LOGGER)
    def test_15_webhook_last_state_tracked_on_record(self):
        """After dispatch, webhook_last_state/webhook_last_sent_date
        reflect success or failure on the triggering record."""
        self.rule_callback.active = False

        record_ok = self._new_record()
        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()):
            record_ok.write({"state": "done"})
        self.assertEqual(record_ok.webhook_last_state, "done")
        self.assertTrue(record_ok.webhook_last_sent_date)

        record_fail = self._new_record()
        with patch(REQUESTS_PATH, side_effect=Exception("Connection refused")):
            record_fail.write({"state": "done"})
        self.assertEqual(record_fail.webhook_last_state, "failed")
        self.assertTrue(record_fail.webhook_last_sent_date)

    # ----- payload template format tests -----

    def test_16_format_label_returns_selection_label(self):
        """'{field:label}' sends the translated label, not the raw value."""
        record = self._new_record(state="done")

        self.assertEqual(
            self.Record._resolve_field_value(record, "{state:label}"), "Done"
        )
        # without the format, the raw value is still sent
        self.assertEqual(self.Record._resolve_field_value(record, "{state}"), "done")

    @mute_logger(MIXIN_LOGGER)
    def test_17_format_join_crosses_x2many(self):
        """'{path:join}' traverses a x2many and joins every value."""
        record = self._new_record(tag_ids=[(6, 0, (self.tag_a | self.tag_b).ids)])

        self.assertEqual(
            self.Record._resolve_field_value(record, "{tag_ids.name:join}"),
            "Webhook Tag A, Webhook Tag B",
        )
        # the plain form cannot traverse it
        self.assertIsNone(self.Record._resolve_field_value(record, "{tag_ids.name}"))
        # unset values are left out, 0 is kept
        record.write({"note": False, "amount": 0})
        self.assertEqual(self.Record._resolve_field_value(record, "{note:join}"), "")
        self.assertEqual(self.Record._resolve_field_value(record, "{amount:join}"), "0")

    def test_18_format_date_and_text(self):
        """':date' keeps the date part only, ':text' converts html to text."""
        record = self._new_record(note="<p>Hello <b>world</b></p>")

        self.assertEqual(
            self.Record._resolve_field_value(record, "{create_date:date}"),
            str(record.create_date.date()),
        )
        # html2plaintext keeps markdown-like markers for <b>/<strong>/<em>
        self.assertEqual(
            self.Record._resolve_field_value(record, "{note:text}"), "Hello *world*"
        )

    def test_19_format_empty_value(self):
        """A path resolving to nothing returns an empty string, not None."""
        record = self._new_record()

        self.assertEqual(self.Record._resolve_field_value(record, "{note:text}"), "")

    # ----- payload method call tests -----

    def test_20_method_call_with_and_without_args(self):
        """'{@_webhook_method}' calls the method on the record."""
        record = self._new_record(name="my-function")

        self.assertEqual(
            self.Record._resolve_field_value(record, "{@_webhook_echo}"), "my-function"
        )
        self.assertEqual(
            self.Record._resolve_field_value(record, "{@_webhook_echo(one, two)}"),
            "one|two",
        )

    @mute_logger(MIXIN_LOGGER)
    def test_21_method_call_guarded(self):
        """Only '_webhook_*' methods are callable, and a raising method is
        swallowed into None instead of blocking the write()."""
        record = self._new_record()

        # not a '_webhook_*' name -> not a template at all, passes through
        self.assertEqual(
            self.Record._resolve_field_value(record, "{@unlink}"), "{@unlink}"
        )
        # unknown '_webhook_*' method -> None
        self.assertIsNone(
            self.Record._resolve_field_value(record, "{@_webhook_missing}")
        )
        # method raising -> None
        self.assertIsNone(self.Record._resolve_field_value(record, "{@_webhook_boom}"))

    def test_22_method_call_inside_payload(self):
        """Method templates resolve at any nesting level of the payload."""
        record = self._new_record(name="nested")

        payload = self.Record._resolve_payload_value(
            record, {"data": {"key": "{@_webhook_echo}", "state": "{state:label}"}}
        )
        self.assertEqual(payload["data"], {"key": "nested", "state": "Draft"})

    # ----- rules cache and access -----

    def test_23_rules_are_cached_per_model(self):
        """Rules are read once per model, and edits apply at once"""
        record = self._new_record()
        self.env["webhook.outbound.rule"]._get_trigger_specs(record._name)
        Rule = type(self.env["webhook.outbound.rule"])
        with patch.object(
            Rule, "search", autospec=True, side_effect=Rule.search
        ) as search:
            record.write({"amount": 1})
            record.write({"amount": 2})
        search.assert_not_called()

        self.rule_callback.active = False
        self.rule_static.trigger_domain = "[('amount', '=', 3)]"
        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"amount": 3})
        mock_post.assert_called_once()

    def test_24_callback_url_is_admin_only(self):
        """A regular user cannot redirect webhooks (and their Authorization
        header) by writing the callback URL, but still triggers webhooks"""
        self.rule_callback.active = False
        self.rule_static.auth_header = "Bearer secret"
        user = new_test_user(self.env, login="webhook_writer")
        record = self._new_record().with_user(user)

        with self.assertRaises(AccessError):
            record.write({"callback_url": "https://attacker.example.com"})
        with self.assertRaises(AccessError):
            self.rule_static.with_user(user).read(["auth_header"])

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args[1]["headers"]["Authorization"], "Bearer secret"
        )
        # Users can read the logs but not change them
        log = self._send_logs().with_user(user)
        self.assertEqual(log.state, "done")
        with self.assertRaises(AccessError):
            log.write({"state": "failed"})

    @mute_logger(MIXIN_LOGGER)
    def test_25_inactive_rule_ignored_without_active_test(self):
        """Archived rules never fire, even when the first write that fills the
        rules cache runs with active_test=False"""
        self.rule_static.active = False
        record = self._new_record().with_context(active_test=False)

        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            record.write({"state": "done"})

        mock_post.assert_not_called()

    def test_26_callback_url_linked_for_create_update_only(self):
        """Ids returned by call_function are not trusted to link a callback URL"""
        record = self._new_record()
        controller = WebhookController()
        request = MagicMock(env=self.env)
        vals = {"callback_url": CALLBACK_URL, "is_create_log": False}
        res = {"is_success": True, "result": {"id": record.id}}
        with (
            patch("odoo.addons.usability_webhooks.controllers.main.request", request),
            patch.object(WebhookController, "_call_function_api", return_value=res),
        ):
            controller._create_api_logs(record._name, dict(vals), "call_function")
            self.assertFalse(record.callback_url)
            controller._create_api_logs(record._name, dict(vals), "create_data")
            self.assertEqual(record.callback_url, CALLBACK_URL)

    def test_27_allowed_callback_url_required_for_record_rules(self):
        """A record callback rule needs a valid http(s) Allowed Callback URL"""
        Rule = self.env["webhook.outbound.rule"]
        vals = {
            "name": "Callback Rule",
            "model_id": self.record_model_id,
            "trigger_domain": "[('state', '=', 'done')]",
            "endpoint_source": "record",
        }
        for allowed in (False, "partner.example.com", "ftp://partner.example.com"):
            with self.assertRaises(ValidationError):
                Rule.create(dict(vals, allowed_callback_url=allowed))
        with self.assertRaises(ValidationError):
            self.rule_callback.allowed_callback_url = False
        # endpoint_source defaults to 'record'
        with self.assertRaises(ValidationError):
            Rule.create({k: v for k, v in vals.items() if k != "endpoint_source"})
        # Not needed for a static endpoint
        Rule.create(dict(vals, endpoint_source="static", endpoint_url=STATIC_URL))

    def test_28_callback_url_matching(self):
        """Same scheme, host and port, and a path inside the allowed path"""
        self.rule_callback.allowed_callback_url = "https://partner.example.com/webhook"
        allowed = (
            "https://partner.example.com/webhook",
            "https://partner.example.com/webhook/",
            "https://partner.example.com/webhook/so/12?token=x",
            "HTTPS://Partner.Example.com/webhook/so",
            "https://partner.example.com:443/webhook/so",
        )
        refused = (
            "http://partner.example.com/webhook",
            "https://partner.example.com.evil.io/webhook",
            "https://partner.example.com@evil.io/webhook",
            # urllib.parse reads host 'partner.example.com', requests sends to evil.io
            "https://evil.io\\@partner.example.com/webhook",
            "https://user:pass@partner.example.com/webhook",
            "https://evil.io/partner.example.com/webhook",
            "https://sub.partner.example.com/webhook",
            "https://partner.example.com:8443/webhook",
            "https://partner.example.com:99999/webhook",
            "https://partner.example.com/webhooks",
            "https://partner.example.com/other",
            "https://partner.example.com/webhook/../admin",
            "https://partner.example.com/webhook/%2e%2e/admin",
            # Receivers decoding twice, or reading '\\' as a separator
            "https://partner.example.com/webhook/%252e%252e/admin",
            "https://partner.example.com/webhook/a%5c..%5c..%5cadmin",
            "https://partner.example.com/webhook\\..\\admin",
            " https://partner.example.com/webhook",
            "https://partner.example.com/webhook/x\n",
            "ftp://partner.example.com/webhook",
            "http://169.254.169.254/latest/meta-data",
            "",
            False,
        )
        for url in allowed:
            with self.subTest(url=url):
                self.assertTrue(self.rule_callback._is_callback_url_allowed(url))
        for url in refused:
            with self.subTest(url=url):
                self.assertFalse(self.rule_callback._is_callback_url_allowed(url))
        # Root path allows any path of the host
        self.rule_callback.allowed_callback_url = "https://partner.example.com/"
        self.assertTrue(
            self.rule_callback._is_callback_url_allowed(
                "https://partner.example.com/any/path"
            )
        )

    @mute_logger(SERVICE_LOGGER)
    def test_29_callback_url_outside_allowed_not_sent(self):
        """A callback URL outside the Allowed Callback URL is not called:
        no payload, no Authorization header, a failed log instead"""
        self.rule_static.active = False
        self.rule_callback.auth_header = "Bearer secret"
        record = self._new_record()
        record.with_context(_webhook_outbound_dispatching=True).write(
            {"callback_url": "https://u:p@attacker.example.com/collect?t=1\nx"}
        )
        Record = type(record)
        with (
            patch(REQUESTS_PATH) as mock_post,
            patch.object(Record, "_build_payload", autospec=True) as build_payload,
        ):
            record.write({"state": "done"})

        mock_post.assert_not_called()
        build_payload.assert_not_called()
        # Logged without userinfo, query nor control characters, and without
        # the allowed URL (internal users can read API logs)
        log = self._send_logs("https://attacker.example.com/collect")
        self.assertEqual(log.state, "failed")
        self.assertIn("outside the Allowed Callback URL", log.result_preview)
        self.assertNotIn("caller.example.com", log.result_preview)
        self.assertNotIn("u:p", log.result_preview)
        self.assertFalse(log.data_preview)
        self.assertEqual(record.webhook_last_state, "failed")
        # The service refuses it too, when called directly
        with patch(REQUESTS_PATH) as mock_post:
            log = self.env["webhook.outbound.service"]._push(
                record, "https://attacker.example.com/x", {}, self.rule_callback
            )
        mock_post.assert_not_called()
        self.assertEqual(log.state, "failed")

        # A rule migrated without Allowed Callback URL does not send either
        self.env.cr.execute(
            "UPDATE webhook_outbound_rule SET allowed_callback_url = NULL "
            "WHERE id = %s",
            (self.rule_callback.id,),
        )
        self.env.invalidate_all()
        record = self._new_record()
        record.with_context(_webhook_outbound_dispatching=True).write(
            {"callback_url": CALLBACK_URL}
        )
        with patch(REQUESTS_PATH) as mock_post:
            record.write({"state": "done"})
        mock_post.assert_not_called()
        self.assertEqual(record.webhook_last_state, "failed")

    @mute_logger(SERVICE_LOGGER)
    def test_30_callback_redirect_not_followed(self):
        """An allowed callback URL may redirect elsewhere: not followed, so the
        payload is not re-sent to another host (307/308 keep the body)"""
        self.rule_static.active = False
        record = self._new_record()
        record.with_context(_webhook_outbound_dispatching=True).write(
            {"callback_url": CALLBACK_URL}
        )
        resp = self._mock_ok_response()
        resp.status_code = 307
        resp.is_redirect = True
        resp.headers = {"Location": "https://attacker.example.com/collect"}

        with patch(REQUESTS_PATH, return_value=resp) as mock_post:
            record.write({"state": "done"})

        self.assertFalse(mock_post.call_args[1]["allow_redirects"])
        log = self._send_logs(CALLBACK_URL)
        self.assertEqual(log.state, "failed")
        self.assertIn("not followed", log.result_preview)
        # Static endpoints, set by an administrator, still follow redirects
        self.rule_static.active = True
        self.rule_callback.active = False
        with patch(REQUESTS_PATH, return_value=self._mock_ok_response()) as mock_post:
            self._new_record().write({"state": "done"})
        self.assertTrue(mock_post.call_args[1]["allow_redirects"])
