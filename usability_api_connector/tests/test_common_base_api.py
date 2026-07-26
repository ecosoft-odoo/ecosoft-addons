# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import warnings
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

REQUESTS_PATH = "odoo.addons.usability_api_connector.models.common_base_api.requests"


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
