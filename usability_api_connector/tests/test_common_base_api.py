# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import warnings
from unittest.mock import MagicMock, patch

import requests
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.service.model import call_kw
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger

BASE_API_PATH = "odoo.addons.usability_api_connector.models.common_base_api"
REQUESTS_PATH = f"{BASE_API_PATH}.requests"


class TestCommonBaseApi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_config = cls.env["api.config"].create(
            {
                "name": "Plain config values",
                "code": "plain_config_values",
                "api_type": "rest_api",
                "endpoint_system": "external",
                "endpoint_url": "https://api-123.example.com",
                "route_path": "/v1/documents",
                "method": "post",
            }
        )
        cls.user = new_test_user(cls.env, login="api_connector_user")

    def _get_last_log(self):
        return self.env["api.connector.log"].search(
            [("api_code", "=", self.api_config.code)],
            order="id desc",
            limit=1,
        )

    def _mock_response(self, data):
        response = MagicMock()
        response.json.return_value = data
        return response

    def test_rest_api_sends_json_to_plain_endpoint_url_without_warning(self):
        response = MagicMock()
        payload = {"name": "Document 1"}

        with (
            warnings.catch_warnings(record=True) as caught,
            patch(f"{REQUESTS_PATH}.request", return_value=response) as request,
        ):
            warnings.simplefilter("always")
            result = self.api_config._execute_rest_api(
                self.api_config, "token", payload
            )

        self.assertEqual(result, response)
        request.assert_called_once_with(
            method="POST",
            url="https://api-123.example.com/v1/documents",
            headers={},
            timeout=30,
            json=payload,
        )
        self.assertFalse(
            any("invalid decimal literal" in str(item.message) for item in caught)
        )

    def test_callback_url_is_used_as_plain_text(self):
        callback_url = "https://callback-123.example.com/result"
        self.api_config.callback_url = callback_url

        with patch(f"{REQUESTS_PATH}.post") as post:
            self.api_config._handle_callback(self.api_config, {"id": 1})

        post.assert_called_once_with(
            callback_url,
            json={"status": "success", "result": {"id": 1}},
            timeout=10,
        )

    def test_static_auth_token_is_used_as_plain_text(self):
        auth_token = "header.payload-123.signature"
        self.api_config.write(
            {
                "auth_required": True,
                "auth_method": "static_token",
                "auth_token": auth_token,
                "python_code": "{}",
            }
        )

        model_class = type(self.api_config)
        with patch.object(
            model_class,
            "_execute_api_request",
            return_value={"is_success": True},
        ) as execute:
            self.api_config.action_call_api(self.api_config.code)

        self.assertEqual(execute.call_args.args[1], auth_token)

    def test_api_log_content_is_formatted_as_indented_json(self):
        payload = {"name": "เอกสารทดสอบ", "items": [{"quantity": 1}]}
        result = {"is_success": True, "id": 10}

        self.api_config._create_api_log(
            api_data=self.api_config,
            payload=payload,
            state="success",
            result=result,
        )

        log = self._get_last_log()
        self.assertEqual(
            log.payload,
            '{\n  "name": "เอกสารทดสอบ",\n  "items": [\n    {\n'
            '      "quantity": 1\n    }\n  ]\n}',
        )
        self.assertEqual(
            log.result,
            '{\n  "is_success": true,\n  "id": 10\n}',
        )

    def test_existing_python_repr_log_is_pretty_printed_for_display(self):
        log = self.env["api.connector.log"].create(
            {
                "api_code": self.api_config.code,
                "state": "success",
                "payload": "{'name': 'Document 1', 'active': True}",
                "result": "plain response",
            }
        )

        self.assertEqual(
            log.payload_display,
            '{\n  "name": "Document 1",\n  "active": true\n}',
        )
        self.assertEqual(log.result_display, "plain response")

    @mute_logger(BASE_API_PATH)
    def test_http_error_saves_response_body_in_existing_log(self):
        self.api_config.write({"python_code": "{}", "save_log": True})
        response = MagicMock()
        response.text = '{"message": "Buyer tax ID is required"}'
        response.raise_for_status.side_effect = requests.HTTPError(
            "417 Client Error: EXPECTATION FAILED",
            response=response,
        )

        with patch(f"{REQUESTS_PATH}.request", return_value=response):
            notification = self.api_config.action_call_api(self.api_config.code)

        log = self._get_last_log()
        self.assertEqual(log.state, "failed")
        self.assertIn("HTTP error: 417 Client Error", log.error_message)
        self.assertIn("Buyer tax ID is required", log.error_message)
        self.assertIn("Buyer tax ID is required", notification["params"]["message"])

    def test_call_api_evaluates_payload_params_and_headers(self):
        self.api_config.write(
            {
                "auth_required": True,
                "auth_method": "static_token",
                "auth_token": "secret-token",
                "headers": '{"Authorization": f"Bearer {auth_token}"}',
                "python_code": '{"name": rec.name, "items": [{"qty": 1}]}',
                "params_code": '{"code": rec.code}',
                "is_form_data": True,
                "save_log": True,
            }
        )
        model_class = type(self.api_config)
        with (
            patch(
                f"{REQUESTS_PATH}.request",
                return_value=self._mock_response({"is_success": True, "id": 7}),
            ) as request,
            patch.object(
                model_class,
                "_get_payload_globals_dict",
                autospec=True,
                side_effect=model_class._get_payload_globals_dict,
            ) as globals_dict,
        ):
            notification = self.api_config.action_call_api(self.api_config.code)

        self.assertEqual(notification["params"]["type"], "success")
        # Payload and params share one evaluation context
        self.assertEqual(globals_dict.call_count, 1)
        request.assert_called_once_with(
            method="POST",
            url="https://api-123.example.com/v1/documents",
            headers={"Authorization": "Bearer secret-token"},
            timeout=30,
            data={"name": "Plain config values", "items": '[{"qty": 1}]'},
            params={"code": "plain_config_values"},
        )
        self.assertEqual(self.api_config.api_status, "success")
        self.assertIn('"id": 7', self.api_config.api_result)
        self.assertEqual(self._get_last_log().state, "success")

    def test_get_request_merges_payload_into_params_and_skips_ssl(self):
        self.api_config.write({"method": "get", "disable_ssl": True})

        with patch(f"{REQUESTS_PATH}.request") as request:
            self.api_config._execute_rest_api(
                self.api_config, False, {"page": 1}, params={"lang": "th"}
            )

        request.assert_called_once_with(
            method="GET",
            url="https://api-123.example.com/v1/documents",
            headers={},
            timeout=30,
            params={"page": 1, "lang": "th"},
            verify=False,
        )

    def test_result_mapping_marks_failure_with_nested_message(self):
        self.api_config.write(
            {
                "python_code": "{}",
                "save_log": True,
                "result_success_key": "result.status",
                "result_success_value": "ok",
                "result_message_key": "result.errors.0",
            }
        )
        response = self._mock_response(
            {"result": {"status": "error", "errors": ["Invalid buyer"]}}
        )

        with patch(f"{REQUESTS_PATH}.request", return_value=response):
            notification = self.api_config.action_call_api(self.api_config.code)

        self.assertEqual(notification["params"]["type"], "danger")
        self.assertEqual(notification["params"]["message"], "Invalid buyer")
        self.assertEqual(self.api_config.api_status, "failed")
        self.assertEqual(self.api_config.api_result, "Invalid buyer")
        log = self._get_last_log()
        self.assertEqual(log.state, "failed")
        self.assertEqual(log.error_message, "Invalid buyer")

    @mute_logger(BASE_API_PATH)
    def test_invalid_payload_expression_is_logged_as_failure(self):
        self.api_config.python_code = "{'name': rec.missing_field}"

        with patch(f"{REQUESTS_PATH}.request") as request:
            notification = self.api_config.action_call_api(self.api_config.code)

        request.assert_not_called()
        self.assertEqual(notification["params"]["type"], "danger")
        self.assertIn("'JSON / Payload'", notification["params"]["message"])
        self.assertEqual(self.api_config.api_status, "failed")
        # Unexpected errors are always logged, even without save_log
        log = self._get_last_log()
        self.assertEqual(log.state, "failed")
        self.assertIn("'JSON / Payload'", log.error_message)

    @mute_logger(BASE_API_PATH)
    def test_unknown_code_is_reported(self):
        notification = self.api_config.action_call_api("unknown_code")

        self.assertEqual(notification["params"]["type"], "danger")
        self.assertIn("unknown_code", notification["params"]["message"])

    def test_api_code_is_unique(self):
        duplicate = self.api_config.copy()
        self.assertFalse(duplicate.code)

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            duplicate.code = self.api_config.code
            duplicate.flush_recordset()

    def test_api_log_count_and_latest_log(self):
        self.assertEqual(self.api_config.api_log_count, 0)
        first = self.api_config._create_api_log(self.api_config, {}, "failed")
        second = self.api_config._create_api_log(self.api_config, {}, "success")
        # Logs of another record are not counted
        other_config = self.api_config.copy({"code": "other_config"})
        other_config._create_api_log(other_config, {}, "success")

        self.assertEqual(self.api_config.api_log_count, 2)
        self.assertEqual(self.api_config.api_log_ids, first | second)
        self.assertEqual(self.api_config._get_latest_api_log(), second)
        action = self.api_config.action_view_api_logs()
        self.assertEqual(
            self.env["api.connector.log"].search(action["domain"]), first | second
        )

    def test_log_limit_from_system_parameter(self):
        self.env["ir.config_parameter"].set_int("api_connector.log_limit", 5)

        log = self.api_config._create_api_log(
            self.api_config, None, "success", result="0123456789"
        )

        self.assertEqual(log.result, "01234")
        self.assertFalse(log.payload)

    def test_configuration_is_admin_only(self):
        api_config_as_user = self.env["api.config"].with_user(self.user)

        with self.assertRaises(AccessError):
            api_config_as_user.search([])
        with self.assertRaises(AccessError):
            self.api_config.with_user(self.user).write({"python_code": "{}"})
        # Configurations are read as superuser, so the call is not RPC-callable,
        # even for administrators
        with (
            patch(f"{REQUESTS_PATH}.request") as request,
            self.assertRaises(AccessError),
        ):
            call_kw(
                self.env["api.config"],
                "action_call_api",
                [self.api_config.ids, self.api_config.code],
                {},
            )
        request.assert_not_called()
        # Regular users still call APIs from server-side code
        self.assertEqual(
            api_config_as_user._get_api_config(self.api_config.code),
            self.api_config,
        )

    def test_user_can_read_but_not_change_logs(self):
        log = self.api_config._create_api_log(self.api_config, {}, "success")
        log_as_user = log.with_user(self.user)

        self.assertEqual(log_as_user.state, "success")
        with self.assertRaises(AccessError):
            log_as_user.write({"state": "failed"})
        with self.assertRaises(AccessError):
            log_as_user.unlink()
