# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

import psycopg2
from odoo_test_helper import FakeModelLoader

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


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

    def test_06e_call_function_private_method_rejected(self):
        """call_function rejects '_' methods, same as RPC call_kw"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {
                "method": "_write",
                "parameter": {"vals": {"function_name": "Hacked"}},
            },
        }
        with self.assertRaisesRegex(AccessError, "Private methods"):
            self.webhook_utils.call_function(self.api_log_model, vals)
        self.assertEqual(self.test_log.function_name, "Common Test")

    def test_06f_call_function_api_private_rejected(self):
        """call_function rejects @api.private methods (e.g. sudo)"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {"method": "sudo"},
        }
        with self.assertRaisesRegex(AccessError, "Private methods"):
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

    # ----- dry run -----

    def test_11_dry_run_create_data(self):
        """dry_run create returns success but persists nothing"""
        Log = self.env[self.api_log_model]
        count = Log.search_count([])
        vals = {"payload": {"log_type": "receive", "function_name": "Dry Run"}}
        result = self.webhook_utils.dry_run(self.api_log_model, vals, "create_data")
        self.assertTrue(result["is_success"])
        self.assertFalse(Log.browse(result["result"]["id"]).exists())
        self.assertEqual(Log.search_count([]), count)

    def test_12_dry_run_update_data(self):
        """dry_run update does not change the record"""
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {"function_name": "Changed"},
        }
        result = self.webhook_utils.dry_run(self.api_log_model, vals, "update_data")
        self.assertTrue(result["is_success"])
        self.assertEqual(self.test_log.function_name, "Common Test")

    def test_13_dry_run_error_raised(self):
        """dry_run raises the same error as a normal call and rolls back its
        own savepoint (no assertRaises: it would add one)"""
        Log = self.env[self.api_log_model]
        count = Log.search_count([])
        vals = {"payload": {"log_type": "wrong", "function_name": "Dry Run"}}
        Utils = type(self.webhook_utils)
        create_data = Utils.create_data

        def write_then_create(utils, model, vals):
            utils.env[model].create({"function_name": "Written before error"})
            return create_data(utils, model, vals)

        with patch.object(Utils, "create_data", write_then_create):
            try:
                self.webhook_utils.dry_run(self.api_log_model, vals, "create_data")
            except ValueError as error:
                self.assertIn("wrong", str(error))
            else:
                self.fail("ValueError not raised")
        self.assertEqual(Log.search_count([]), count)
        # Database error at flush (name is NOT NULL): cursor still usable
        Subtype = self.env["mail.message.subtype"]
        subtype_count = Subtype.search_count([])
        vals = {"payload": {"description": "No name"}}
        with mute_logger("odoo.sql_db"):
            try:
                self.webhook_utils.dry_run("mail.message.subtype", vals, "create_data")
            except psycopg2.IntegrityError as error:
                self.assertIn("name", str(error))
            else:
                self.fail("IntegrityError not raised")
        self.assertEqual(Subtype.search_count([]), subtype_count)
        self.assertEqual(Log.search_count([]), count)

    def test_14_dry_run_sequence_no_gap_not_consumed(self):
        """dry_run does not consume no_gap sequence (standard Odoo rollback)"""
        seq = self.env["ir.sequence"].create(
            {
                "name": "Dry Run",
                "prefix": "DRY",
                "padding": 3,
                "implementation": "no_gap",
            }
        )
        vals = {
            "search_key": {"id": seq.id},
            "payload": {"method": "next_by_id"},
        }
        result = self.webhook_utils.dry_run("ir.sequence", vals, "call_function")
        self.assertEqual(result["result"], "DRY001")
        self.assertEqual(seq.next_by_id(), "DRY001")

    def test_15_dry_run_auto_create_no_stale_lookup(self):
        """Lookup cached during dry_run auto_create must not survive rollback,
        else next real call links a record that no longer exists"""
        Subtype = self.env["mail.message.subtype"]
        # Browse again: test_log class predates FakeModelLoader (subtype_test_id)
        log = self.env[self.api_log_model].browse(self.test_log.id)
        vals = {
            "search_key": {"id": log.id},
            "payload": {"subtype_test_id": {"name": "Dry Run Subtype"}},
            "auto_create": {"subtype_test_id": {"name": "Dry Run Subtype"}},
        }
        result = self.webhook_utils.dry_run(self.api_log_model, vals, "update_data")
        self.assertTrue(result["is_success"])
        self.assertFalse(Subtype.search([("name", "=", "Dry Run Subtype")]))
        self.assertFalse(log.subtype_test_id)
        # Real call: auto_create again and link the new record
        self.webhook_utils.update_data(self.api_log_model, vals)
        self.env.flush_all()
        subtype = Subtype.search([("name", "=", "Dry Run Subtype")])
        self.assertEqual(len(subtype), 1)
        self.assertEqual(log.subtype_test_id, subtype)

    def test_16_dry_run_resets_ormcache(self):
        """Any ormcache filled during dry_run is dropped after rollback (same as
        base_import dryrun), other workers are not asked to clear theirs"""
        Log = self.env[self.api_log_model]
        registry = self.env.registry
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {
                "method": "action_create_cached_category",
                "parameter": {"name": "Cached Tag"},
            },
        }
        # As in a fresh request: FakeModelLoader and earlier tests leave
        # invalidation flags on this thread, start from known ones instead
        self.addCleanup(
            setattr, registry, "registry_invalidated", registry.registry_invalidated
        )
        self.addCleanup(
            registry.cache_invalidated.update, set(registry.cache_invalidated)
        )
        registry.registry_invalidated = False
        registry.cache_invalidated.clear()
        registry.cache_invalidated.add("assets")  # invalidated before dry run
        result = self.webhook_utils.dry_run(self.api_log_model, vals, "call_function")
        self.assertFalse(registry.registry_invalidated)
        self.assertEqual(len(result["result"]), 1)
        self.assertFalse(Log._test_lookup_category_ids("Cached Tag"))
        # Only what was invalidated before the dry run is signaled
        self.assertEqual(registry.cache_invalidated, {"assets"})

    # ----- lookup memo -----

    def test_17_lookup_memo_within_one_call(self):
        """Same lookup is searched once per API call"""
        Tag = self.env["res.partner.category"]
        tag = Tag.create({"name": "Webhook Tag A"})
        utils = self.webhook_utils._with_lookup_memo()
        args = ("name", str(["Webhook Tag A"]))
        found = utils._call_field_search_cache(Tag, *args)
        self.assertEqual(found, tag)
        with patch.object(type(Tag), "search") as search:
            self.assertEqual(utils._call_field_search_cache(Tag, *args), tag)
        search.assert_not_called()

    def test_18_lookup_memo_per_user(self):
        """Memo never gives a user a record hidden by its record rules"""
        Tag = self.env["res.partner.category"]
        hidden = Tag.create({"name": "Hidden Tag"})
        group_user = self.env.ref("base.group_user")
        user = self.env["res.users"].create(
            {
                "name": "Webhook User",
                "login": "webhook_memo_user",
                "groups_id": [Command.set(group_user.ids)],
            }
        )
        self.env["ir.rule"].create(
            {
                "name": "Hide tag",
                "model_id": self.env["ir.model"]._get_id("res.partner.category"),
                "groups": [Command.set(group_user.ids)],
                "domain_force": f"[('id', '!=', {hidden.id})]",
            }
        )
        args = ("name", str(["Hidden Tag"]))
        # Same memo dict for both users, as worst case
        utils = self.webhook_utils._with_lookup_memo()
        self.assertEqual(utils._call_field_search_cache(Tag, *args), hidden)
        found = utils.with_user(user)._call_field_search_cache(
            Tag.with_user(user), *args
        )
        self.assertFalse(found)

    def test_19_no_registry_cache_clear(self):
        """create/search must not clear the registry-wide ormcache"""
        self.env["mail.message.subtype"].create({"name": "Webhook Subtype"})
        Registry = type(self.env.registry)
        with (
            patch.object(Registry, "clear_cache") as clear_cache,
            patch.object(Registry, "clear_all_caches") as clear_all_caches,
        ):
            self.webhook_utils.create_data(
                self.api_log_model,
                {
                    "payload": {
                        "function_name": "No Clear Cache",
                        "subtype_test_id": {"name": "Webhook Subtype"},
                    }
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
        clear_all_caches.assert_not_called()

    def test_20_dry_run_only_public_functions(self):
        """dry_run dispatches public webhook.utils functions only"""
        vals = {"search_key": {"id": self.test_log.id}}
        for function in ("_search_object", "dry_run"):
            with self.assertRaisesRegex(AccessError, "Private methods"):
                self.webhook_utils.dry_run(self.api_log_model, vals, function)

    def test_21_dry_run_hooks(self):
        """Hooks added during a dry run are dropped (they may send or write
        without the dry run guards). Hooks and data registered before are kept
        as they were"""
        cr = self.env.cr
        before = []
        cr.postcommit.data["webhook.test"] = before
        cr.postcommit.add(lambda: None)
        hooks = (cr.prerollback, cr.postcommit, cr.postrollback)
        count = len(cr.postcommit._funcs)
        vals = {
            "search_key": {"id": self.test_log.id},
            "payload": {"method": "action_add_hooks"},
        }
        Log = type(self.env[self.api_log_model])
        with patch.object(Log, "_test_on_rollback") as on_rollback:
            result = self.webhook_utils.dry_run(
                self.api_log_model, vals, "call_function"
            )
        self.assertTrue(result["result"])
        on_rollback.assert_not_called()
        self.assertEqual((cr.prerollback, cr.postcommit, cr.postrollback), hooks)
        self.assertEqual(len(cr.postcommit._funcs), count)
        self.assertIs(cr.postcommit.data["webhook.test"], before)
        self.assertFalse(before)

    def test_22_lookup_memo_per_context(self):
        """Memo is per search environment, e.g. active_test"""
        Tag = self.env["res.partner.category"]
        archived = Tag.create({"name": "Archived Tag", "active": False})
        utils = self.webhook_utils._with_lookup_memo()
        args = ("name", str(["Archived Tag"]))
        found = utils._call_field_search_cache(
            Tag.with_context(active_test=False), *args
        )
        self.assertEqual(found, archived)
        self.assertFalse(utils._call_field_search_cache(Tag, *args))

    def test_23_lookup_memo_cleared_after_create(self):
        """A created record is seen by the next lookup of the same call"""
        Tag = self.env["res.partner.category"]
        Tag.create({"name": "Dup Tag"})
        utils = self.webhook_utils._with_lookup_memo()
        args = ("name", str(["Dup Tag"]))
        self.assertEqual(len(utils._call_field_search_cache(Tag, *args)), 1)
        utils.friendly_create_data(
            "res.partner.category", {"payload": {"name": "Dup Tag"}}
        )
        self.assertEqual(len(utils._call_field_search_cache(Tag, *args)), 2)
