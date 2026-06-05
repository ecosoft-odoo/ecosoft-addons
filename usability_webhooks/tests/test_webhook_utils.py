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
        """Test creating a new log via webhook"""
        vals = {
            "payload": {
                "log_type": "receive",
                "function_name": "Test Input",
            }
        }
        result = self.webhook_utils.create_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        self.assertTrue(result["result"]["id"])

        # Verify created record
        record = self.env[self.api_log_model].browse(result["result"]["id"])
        self.assertEqual(record.function_name, "Test Input")

    def test_02_update_data(self):
        """Test updating existing log via webhook"""
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

        # Verify updated record
        self.assertEqual(self.test_log.function_name, "Updated Function")

    def test_03_search_data(self):
        """Test searching log via webhook"""
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
        """Test creating record with many2one using dict lookup format"""
        vals = {
            "payload": {
                "log_type": "receive",
                "function_name": "Test New Group",
                # many2one: {"lookup_field": "value"}
                "subtype_test_id": {"name": "Test New Subtype"},
            },
            "auto_create": {"subtype_test_id": {"name": "Test New Subtype"}},
        }
        result = self.webhook_utils.create_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])

    def test_04b_create_with_many2one_by_id(self):
        """Test creating record with many2one using explicit ID lookup"""
        subtype = self.env["mail.message.subtype"].create({"name": "Subtype By ID"})
        vals = {
            "payload": {
                "log_type": "receive",
                "function_name": "Test By ID",
                # many2one: {"id": <int>}
                "subtype_test_id": {"id": subtype.id},
            },
        }
        result = self.webhook_utils.create_data(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        record = self.env[self.api_log_model].browse(result["result"]["id"])
        self.assertEqual(record.subtype_test_id, subtype)

    def test_04c_create_with_many2many(self):
        """Test many2many add mode using {"mode": "add", "records": [...]}"""
        tag1 = self.env["mail.message.subtype"].create({"name": "Tag M2M One"})
        tag2 = self.env["mail.message.subtype"].create({"name": "Tag M2M Two"})
        Model = self.env["mail.message.subtype"]
        result = self.webhook_utils._process_many2many_field(
            Model,
            {
                "mode": "add",
                "records": [{"name": "Tag M2M One"}, {"name": "Tag M2M Two"}],
            },
            "[]",
            "tag_ids",
            {},
        )
        self.assertIn((4, tag1.id), result)
        self.assertIn((4, tag2.id), result)

    def test_04d_create_with_many2many_replace(self):
        """Test many2many replace mode using {"mode": "replace", "records": [...]}"""
        tag = self.env["mail.message.subtype"].create({"name": "Tag Replace"})
        Model = self.env["mail.message.subtype"]
        result = self.webhook_utils._process_many2many_field(
            Model,
            {"mode": "replace", "records": [{"name": "Tag Replace"}]},
            "[]",
            "tag_ids",
            {},
        )
        self.assertEqual(result, [(6, 0, [tag.id])])

    def test_04e_many2many_default_mode_is_replace(self):
        """Test many2many with no mode specified defaults to replace"""
        tag = self.env["mail.message.subtype"].create({"name": "Tag Default"})
        Model = self.env["mail.message.subtype"]
        result = self.webhook_utils._process_many2many_field(
            Model,
            {"records": [{"name": "Tag Default"}]},
            "[]",
            "tag_ids",
            {},
        )
        self.assertEqual(result, [(6, 0, [tag.id])])

    def test_04f_many2many_invalid_mode_raises(self):
        """Test many2many with invalid mode raises ValidationError"""
        Model = self.env["mail.message.subtype"]
        with self.assertRaises(ValidationError):
            self.webhook_utils._process_many2many_field(
                Model,
                {"mode": "upsert", "records": [{"name": "Tag"}]},
                "[]",
                "tag_ids",
                {},
            )

    def test_05_create_with_attachment(self):
        """Test creating record with attachment"""
        vals = {
            "payload": {
                "log_type": "receive",
                "function_name": "With Attachment",
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

    def test_06b_call_function_with_parameter(self):
        """Test call_function with keyword parameters (order-independent)"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {
                "method": "action_call_api_with_params",
                "parameter": {"b": "world", "a": "hello"},
            },
        }
        result = self.webhook_utils.call_function(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.test_log.function_name, "hello-world-")

    def test_06c_call_function_with_parameter_and_optional(self):
        """Test call_function with keyword parameters including optional arg"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {
                "method": "action_call_api_with_params",
                "parameter": {"a": "foo", "b": "bar", "note": "baz"},
            },
        }
        result = self.webhook_utils.call_function(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.test_log.function_name, "foo-bar-baz")

    def test_06d_call_function_with_context(self):
        """Test call_function passes context into env.context of the record"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {
                "method": "action_call_api_with_context",
                "context": {"is_context": "1"},
            },
        }
        result = self.webhook_utils.call_function(self.api_log_model, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.test_log.function_name, "is_context=1")

    def test_07_invalid_search_key(self):
        """Test error handling for invalid search key"""
        vals = {
            "payload": {
                "function_name": "Test",
            }
        }
        with self.assertRaisesRegex(
            ValidationError, "Parameter 'search_key' in 'vals' not found!"
        ):
            self.webhook_utils.update_data(self.api_log_model, vals)
