# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo_test_helper import FakeModelLoader

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWebhookUtils(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Initialize test data
        cls.webhook_utils = cls.env["webhook.utils"]
        cls.api_log_model = "api.log"

        # Create test log
        cls.test_log = cls.env["api.log"].create(
            {
                "log_type": "receive",
                "function_name": "Common Test",
            }
        )

        # Add inherit api.log for test
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .api_log_tester import APILogTester

        cls.loader.update_registry((APILogTester,))

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_01_create_data(self):
        """Test creating a new group via webhook"""
        vals = {
            "payload": {
                "log_type": "receive",
                "function_name": "Test Input",
            }
        }
        result = self.webhook_utils.create_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        self.assertTrue(result["result"]["id"])

        # Verify created group
        group = self.env[self.api_log_model].browse(result["result"]["id"])
        self.assertEqual(group.function_name, "Test Input")

    def test_02_update_data(self):
        """Test updating existing group via webhook"""
        vals = {
            "search_key": {
                "id": self.test_log.id,
            },
            "payload": {
                "function_name": "Updated Function",
            },
        }
        result = self.webhook_utils.update_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])

        # Verify updated group
        self.assertEqual(self.test_log.function_name, "Updated Function")

    def test_03_search_data(self):
        """Test searching group via webhook"""
        vals = {
            "payload": {
                "search_field": ["function_name"],
                "search_domain": "[('function_name', '=', 'Common Test')]",
                "limit": 1,
            }
        }
        result = self.webhook_utils.search_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        self.assertTrue(result["result"])
        self.assertEqual(result["result"][0]["function_name"], "Common Test")

    def test_04_create_with_many2one(self):
        """Test creating record with many2one relation"""
        vals = {
            "payload": {
                "log_type": "receive",
                "function_name": "Test New Group",
                "subtype_test_id": "Test New Subtype",  # Using name instead of ID
            },
            "auto_create": {"subtype_test_id": {"name": "Test New Subtype"}},
        }
        result = self.webhook_utils.create_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])

    def test_05_create_with_attachment(self):
        """Test creating record with attachment"""
        vals = {
            "payload": {
                "name": "With Attachment",
                "attachment_ids": [
                    {
                        "name": "test.txt",
                        "datas": "SGVsbG8gV29ybGQ=",  # Base64 encoded "Hello World"
                    }
                ],
            }
        }
        result = self.webhook_utils.create_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])

        # Verify attachment
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self.api_log_model),
                ("res_id", "=", result["result"]["id"]),
            ]
        )
        self.assertTrue(attachment)
        self.assertEqual(attachment.name, "test.txt")

    def test_06_call_function(self):
        """Test calling model function via webhook"""
        vals = {
            "search_key": {
                "id": self.test_log.id,
            },
            "payload": {
                "method": "action_call_api",
                "parameter": {},
            },
        }
        result = self.webhook_utils.call_function(self.api_log_model, vals)
        self.assertTrue(result["is_success"])

    def test_07_invalid_search_key(self):
        """Test error handling for invalid search key"""
        vals = {
            "payload": {
                "name": "Test",
            }
        }
        with self.assertRaisesRegex(
            ValidationError, "Parameter 'search_key' in 'vals' not found!"
        ):
            self.webhook_utils.update_data(self.api_log_model, vals)
