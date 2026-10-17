# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo_test_helper import FakeModelLoader

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


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
        record = self.env[self.api_log_model].browse(result["result"]["id"])
        self.assertEqual(record.subtype_test_id.name, "Test New Subtype")

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
                "method": "action_call_api_with_context",
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

    def test_06e_call_function_private_method_blocked(self):
        """Test call_function refuses '_' prefixed and @api.private methods"""
        for method in ("_write", "sudo"):
            vals = {
                "search_key": {"id": self.test_log.id},
                "payload": {"method": method, "parameter": {}},
            }
            with self.assertRaises(AccessError):
                self.webhook_utils.call_function(self.api_log_model, vals)

    def test_06f_call_function_unknown_method(self):
        """Test call_function raises AttributeError for a missing method"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {"method": "action_not_exist"},
        }
        with self.assertRaises(AttributeError):
            self.webhook_utils.call_function(self.api_log_model, vals)

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

    def test_08_unlink_removes_attachment(self):
        """Deleting api.log via ORM unlink also removes its ir.attachment"""
        log = self.env["api.log"].create({"log_type": "receive"})
        log._save_payload("x" * 3000, "y" * 3000)
        attachment_id = log.attachment_id.id
        self.assertTrue(attachment_id)

        log.unlink()

        self.assertFalse(self.env["ir.attachment"].browse(attachment_id).exists())

    def test_09_autovacuum_bulk_removes_attachment(self):
        """autovacuum (bulk mode) also removes ir.attachment of vacuumed logs"""
        log = self.env["api.log"].create({"log_type": "receive"})
        log._save_payload("x" * 3000, "y" * 3000)
        attachment_id = log.attachment_id.id
        log_id = log.id
        self.assertTrue(attachment_id)

        self.env.cr.execute(
            "UPDATE api_log SET create_date = NOW() - INTERVAL '10 days' WHERE id = %s",
            (log_id,),
        )

        self.env["api.log"].autovacuum(days=5)

        self.assertFalse(self.env["api.log"].browse(log_id).exists())
        self.assertFalse(self.env["ir.attachment"].browse(attachment_id).exists())

    def test_10_autovacuum_chunk_removes_attachment(self):
        """autovacuum (chunk mode) also removes ir.attachment of vacuumed logs"""
        log = self.env["api.log"].create({"log_type": "receive"})
        log._save_payload("x" * 3000, "y" * 3000)
        attachment_id = log.attachment_id.id
        log_id = log.id
        self.assertTrue(attachment_id)

        self.env.cr.execute(
            "UPDATE api_log SET create_date = NOW() - INTERVAL '10 days' WHERE id = %s",
            (log_id,),
        )

        self.env["api.log"].autovacuum(days=5, chunk_size=100)

        self.assertFalse(self.env["api.log"].browse(log_id).exists())
        self.assertFalse(self.env["ir.attachment"].browse(attachment_id).exists())

    def test_11_lookup_uses_current_user_rules(self):
        """Lookup result is not shared across users: caller's record rules apply"""
        Subtype = self.env["mail.message.subtype"]
        subtype = Subtype.create({"name": "Hidden Subtype"})
        user = new_test_user(self.env, login="webhook_user", groups="base.group_user")
        self.env["ir.rule"].create(
            {
                "name": "Hide subtype",
                "model_id": self.env.ref("mail.model_mail_message_subtype").id,
                "domain_force": f"[('id', '!=', {subtype.id})]",
                "groups": [(4, self.env.ref("base.group_user").id)],
            }
        )
        args = ("name", str(["Hidden Subtype"]), "[]")
        # Same memo dict for both users, as worst case
        utils = self.webhook_utils._with_lookup_memo()
        found = utils._call_field_search_cache(Subtype, *args)
        self.assertEqual(found, subtype)
        found = utils.with_user(user)._call_field_search_cache(
            Subtype.with_user(user), *args
        )
        self.assertFalse(found)

    def test_12_no_registry_cache_clear(self):
        """create/search must not clear the registry-wide ormcache"""
        Registry = type(self.env.registry)
        with patch.object(Registry, "clear_cache") as clear_cache:
            self.webhook_utils.create_data(
                self.api_log_model,
                {
                    "payload": {
                        "function_name": "No Clear Cache",
                        "subtype_test_id": {"name": "Discussions"},
                    },
                },
            )
            self.webhook_utils.search_data(
                self.api_log_model,
                {
                    "payload": {
                        "search_field": ["function_name", "subtype_test_id{name}"],
                        "search_domain": "[('function_name', '=', 'No Clear Cache')]",
                    }
                },
            )
        clear_cache.assert_not_called()

    def test_13_lookup_memo_within_one_call(self):
        """Same lookup is searched once per API call"""
        Subtype = self.env["mail.message.subtype"]
        utils = self.webhook_utils._with_lookup_memo()
        args = ("name", str(["Discussions"]), "[]")
        found = utils._call_field_search_cache(Subtype, *args)
        self.assertTrue(found)
        with patch.object(type(Subtype), "search") as search:
            self.assertEqual(utils._call_field_search_cache(Subtype, *args), found)
        search.assert_not_called()

    def test_14_ignore_checkcompany_model_exact_match(self):
        """Ignoring 'res.partner.bank' must not skip company check of 'res.partner'"""
        ICP = self.env["ir.config_parameter"]
        other_company = self.env["res.company"].create({"name": "Other Company"})
        self.env["res.partner"].create(
            {"name": "Other Company Partner", "company_id": other_company.id}
        )
        rec = self.env["res.partner.bank"].new()
        rec_dict = {"partner_id": {"name": "Other Company Partner"}}
        # Not listed (or odd values): company check applies, no crash
        for value in ('["res.partner.bank"]', "", "1", "[1, 'res.users']"):
            ICP.set_param("webhook.ignore_checkcompany_model", value)
            with self.assertRaisesRegex(ValidationError, "found no match"):
                self.webhook_utils._finalize_data_to_write(rec, rec_dict)
        # Exact name, JSON list or comma separated
        for value in ('["res.partner"]', "res.users, res.partner"):
            ICP.set_param("webhook.ignore_checkcompany_model", value)
            res = self.webhook_utils._finalize_data_to_write(rec, rec_dict)
            self.assertTrue(res["partner_id"])

    def test_15_search_data_2many_batched(self):
        """Related records of all rows are read in one query, per row result kept"""
        Subtype = self.env["mail.message.subtype"]
        sub1, sub2 = Subtype.create([{"name": "Batch 1"}, {"name": "Batch 2"}])
        self.env["api.log"].create(
            [
                {
                    "function_name": "Batch",
                    "subtype_test_id": sub.id,
                    "reference_test": f"{sub._name},{sub.id}" if sub else False,
                }
                for sub in (sub1, sub2, sub1, Subtype)
            ]
        )
        vals = {
            "payload": {
                "search_field": ["subtype_test_id{name}", "reference_test{name}"],
                "search_domain": "[('function_name', '=', 'Batch')]",
                "order": "id",
            }
        }
        Utils = type(self.webhook_utils)
        with patch.object(
            Utils,
            "_update_child_2many",
            autospec=True,
            side_effect=Utils._update_child_2many,
        ) as update_child:
            result = self.webhook_utils.search_data(self.api_log_model, vals)
        # One query per field, not one per row
        self.assertEqual(update_child.call_count, 2)
        expected = [
            [{"id": sub1.id, "name": "Batch 1"}],
            [{"id": sub2.id, "name": "Batch 2"}],
            [{"id": sub1.id, "name": "Batch 1"}],
            [],
        ]
        rows = result["result"]
        self.assertEqual([row["subtype_test_id"] for row in rows], expected)
        self.assertEqual([row["reference_test"] for row in rows], expected)
        # Empty spec keeps the value as read
        vals["payload"]["search_field"] = ["subtype_test_id{}"]
        result = self.webhook_utils.search_data(self.api_log_model, vals)
        self.assertEqual(result["result"][0]["subtype_test_id"], (sub1.id, "Batch 1"))
