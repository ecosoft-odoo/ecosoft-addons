# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user
from odoo.tools import json_default

from .common import WebhookTestCommon

RECORD = "webhook.test.record"


class TestWebhookUtils(WebhookTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webhook_utils = cls.env["webhook.utils"]

    def _api_log_with_attachment(self):
        log = self.env["api.log"].create({"log_type": "receive"})
        log._save_payload("x" * 3000, "y" * 3000)
        # Full request and response are kept in the attachment
        content = json.loads(log.attachment_id.raw.content)
        self.assertEqual(content, {"data": "x" * 3000, "result": "y" * 3000})
        return log

    def test_01_create_data(self):
        """Test creating a new record via webhook"""
        vals = {
            "payload": {"name": "Test Input"},
            "result_field": ["name", "tag_id"],
        }
        result = self.webhook_utils.create_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        record = self.Record.browse(result["result"]["id"])
        self.assertEqual(record.name, "Test Input")
        # Result fields are read, so the answer can be sent as JSON
        self.assertEqual(
            result["records"],
            [{"id": record.id, "name": "Test Input", "tag_id": False}],
        )
        json.dumps(result, default=json_default)

    def test_02_update_data(self):
        """Test updating existing record via webhook"""
        vals = {
            "search_key": {"id": self.record.id},
            "payload": {"name": "Updated Function"},
        }
        result = self.webhook_utils.update_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        # search_key values are echoed back in the result, but 'id' is the
        # list of updated records
        self.assertEqual(result["result"], {"id": [self.record.id]})
        vals["search_key"] = {"id": [self.record.id, self.record.id + 1000]}
        result = self.webhook_utils.update_data(RECORD, vals)
        self.assertEqual(result["result"], {"id": [self.record.id]})
        self.assertEqual(self.record.name, "Updated Function")

    def test_03_search_data(self):
        """Test searching record via webhook"""
        vals = {
            "payload": {
                "search_field": ["name"],
                "search_domain": "[('name', '=', 'Common Test')]",
                "limit": 1,
            }
        }
        result = self.webhook_utils.search_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(result["result"][0]["name"], "Common Test")

    def test_04_create_with_many2one(self):
        """Test creating record with many2one using dict lookup format"""
        vals = {
            "payload": {
                "name": "Test New Tag",
                # many2one: {"lookup_field": "value"}
                "tag_id": {"name": "Test New Tag"},
            },
            "auto_create": {"tag_id": {"name": "Test New Tag"}},
        }
        result = self.webhook_utils.create_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        record = self.Record.browse(result["result"]["id"])
        self.assertEqual(record.tag_id.name, "Test New Tag")

    def test_04b_create_with_many2one_by_id(self):
        """Test creating record with many2one using explicit ID lookup"""
        vals = {
            "payload": {
                "name": "Test By ID",
                # many2one: {"id": <int>}
                "tag_id": {"id": self.tag_a.id},
            },
        }
        result = self.webhook_utils.create_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        record = self.Record.browse(result["result"]["id"])
        self.assertEqual(record.tag_id, self.tag_a)

    def test_04c_create_with_many2many(self):
        """Test many2many add mode using {"mode": "add", "records": [...]}"""
        result = self.webhook_utils._process_many2many_field(
            self.Tag,
            {
                "mode": "add",
                "records": [{"name": "Webhook Tag A"}, {"name": "Webhook Tag B"}],
            },
            None,
            "tag_ids",
            {},
        )
        self.assertEqual(
            result, [Command.link(self.tag_a.id), Command.link(self.tag_b.id)]
        )

    def test_04d_create_with_many2many_replace(self):
        """Test many2many replace mode using {"mode": "replace", "records": [...]}"""
        result = self.webhook_utils._process_many2many_field(
            self.Tag,
            {"mode": "replace", "records": [{"name": "Webhook Tag A"}]},
            None,
            "tag_ids",
            {},
        )
        self.assertEqual(result, [(6, 0, [self.tag_a.id])])

    def test_04e_many2many_default_mode_is_replace(self):
        """Test many2many with no mode specified defaults to replace"""
        vals = {
            "payload": {
                "name": "Test M2M",
                "tag_ids": {"records": [{"name": "Webhook Tag B"}]},
                "line_ids": [
                    {"name": "Line 1", "tag_id": {"name": "Webhook Tag A"}},
                    {"name": "Line 2"},
                ],
            },
        }
        result = self.webhook_utils.create_data(RECORD, vals)
        record = self.Record.browse(result["result"]["id"])
        self.assertEqual(record.tag_ids, self.tag_b)
        self.assertEqual(record.line_ids.mapped("name"), ["Line 1", "Line 2"])
        self.assertEqual(record.line_ids[0].tag_id, self.tag_a)

    def test_04f_many2many_invalid_mode_raises(self):
        """Test many2many with invalid mode raises ValidationError"""
        with self.assertRaises(ValidationError):
            self.webhook_utils._process_many2many_field(
                self.Tag,
                {"mode": "upsert", "records": [{"name": "Webhook Tag A"}]},
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
        result = self.webhook_utils.create_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        attachment = self.env["ir.attachment"].search(
            [("res_model", "=", RECORD), ("res_id", "=", result["result"]["id"])]
        )
        # Once, with its content, although the model has attachment_ids
        self.assertEqual(attachment.name, "test.txt")
        self.assertEqual(attachment.raw.content, b"Hello World")

    def test_06_call_function(self):
        """Test calling model function via webhook"""
        vals = {
            "search_key": {"id": self.record.id},
            "payload": {"method": "action_with_context", "parameter": {}},
        }
        result = self.webhook_utils.call_function(RECORD, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.record.name, "is_context=none")

    def test_06b_call_function_with_parameter(self):
        """Test call_function with keyword parameters (order-independent)"""
        vals = {
            "search_key": {"id": self.record.id},
            "payload": {
                "method": "action_with_params",
                "parameter": {"b": "world", "a": "hello"},
            },
        }
        result = self.webhook_utils.call_function(RECORD, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.record.name, "hello-world-")

    def test_06c_call_function_with_parameter_and_optional(self):
        """Test call_function with keyword parameters including optional arg"""
        vals = {
            "search_key": {"id": self.record.id},
            "payload": {
                "method": "action_with_params",
                "parameter": {"a": "foo", "b": "bar", "note": "baz"},
            },
        }
        result = self.webhook_utils.call_function(RECORD, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.record.name, "foo-bar-baz")

    def test_06d_call_function_with_context(self):
        """Test call_function passes context into env.context of the record"""
        vals = {
            "search_key": {"id": self.record.id},
            "payload": {
                "method": "action_with_context",
                "context": {"is_context": "1"},
            },
        }
        result = self.webhook_utils.call_function(RECORD, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(self.record.name, "is_context=1")

    def test_06e_call_function_private_method_blocked(self):
        """Test call_function refuses '_' prefixed and @api.private methods"""
        for method in ("_write", "sudo", "_webhook_echo"):
            vals = {
                "search_key": {"id": self.record.id},
                "payload": {"method": method, "parameter": {}},
            }
            with self.assertRaises(AccessError):
                self.webhook_utils.call_function(RECORD, vals)

    def test_06f_call_function_unknown_method(self):
        """Test call_function raises AttributeError for a missing method"""
        vals = {
            "search_key": {"id": self.record.id},
            "payload": {"method": "action_not_exist"},
        }
        with self.assertRaises(AttributeError):
            self.webhook_utils.call_function(RECORD, vals)

    def test_07_invalid_search_key(self):
        """Test error handling for invalid search key"""
        vals = {"payload": {"name": "Test"}}
        with self.assertRaisesRegex(
            ValidationError, "Parameter 'search_key' in 'vals' not found!"
        ):
            self.webhook_utils.update_data(RECORD, vals)

    def test_08_unlink_removes_attachment(self):
        """Deleting api.log via ORM unlink also removes its ir.attachment"""
        log = self._api_log_with_attachment()
        attachment = log.attachment_id

        log.unlink()

        self.assertFalse(attachment.exists())

    def test_09_autovacuum_bulk_removes_attachment(self):
        """autovacuum (bulk mode) also removes ir.attachment of vacuumed logs"""
        old_log = self._api_log_with_attachment()
        attachment = old_log.attachment_id
        new_log = self.env["api.log"].create({"log_type": "receive"})
        self.env.cr.execute(
            "UPDATE api_log SET create_date = NOW() - INTERVAL '10 days' WHERE id = %s",
            (old_log.id,),
        )
        self.env.invalidate_all()

        self.env["api.log"].autovacuum(days=5)

        self.assertFalse(old_log.exists())
        self.assertFalse(attachment.exists())
        self.assertTrue(new_log.exists())

    def test_10_autovacuum_chunk_removes_attachment(self):
        """autovacuum (chunk mode) deletes the oldest logs, at most chunk_size"""
        logs = self.env["api.log"].create([{"log_type": "receive"}] * 3)
        logs[0]._save_payload("x" * 3000, "y" * 3000)
        attachment = logs[0].attachment_id
        for days, log in zip((12, 11, 10), logs, strict=True):
            self.env.cr.execute(
                "UPDATE api_log SET create_date = NOW() - %s * INTERVAL '1 day' "
                "WHERE id = %s",
                (days, log.id),
            )
        self.env.invalidate_all()

        self.env["api.log"].autovacuum(days=5, chunk_size=2)

        self.assertEqual(logs.exists(), logs[2])
        self.assertFalse(attachment.exists())

    def test_11_lookup_uses_current_user_rules(self):
        """Lookup result is not shared across users: caller's access rules apply"""
        hidden = self.Tag.create({"name": "Hidden Tag"})
        user = new_test_user(self.env, login="webhook_user", groups="base.group_user")
        self.env["ir.access"].create(
            {
                "name": "Hide tag",
                "model_id": self.env["ir.model"]._get_id("res.partner.category"),
                "operation": "r",
                "domain": f"[('id', '!=', {hidden.id})]",
            }
        )
        args = ([("name", "in", ["Hidden Tag"])],)
        # Same memo dict for both users, as worst case
        utils = self.webhook_utils._with_lookup_memo()
        found = utils._call_field_search_cache(self.Tag, *args)
        self.assertEqual(found, hidden)
        found = utils.with_user(user)._call_field_search_cache(
            self.Tag.with_user(user), *args
        )
        self.assertFalse(found)

    def test_12_no_registry_cache_clear(self):
        """create/search must not clear the registry-wide ormcache"""
        Transaction = type(self.env.transaction)
        with patch.object(Transaction, "invalidate_ormcache") as invalidate_ormcache:
            self.webhook_utils.create_data(
                RECORD,
                {
                    "payload": {
                        "name": "No Clear Cache",
                        "tag_id": {"name": "Webhook Tag A"},
                    },
                },
            )
            self.webhook_utils.search_data(
                RECORD,
                {
                    "payload": {
                        "search_field": ["name", "tag_id{name}"],
                        "search_domain": "[('name', '=', 'No Clear Cache')]",
                    }
                },
            )
        invalidate_ormcache.assert_not_called()

    def test_13_lookup_memo_within_one_call(self):
        """Same lookup is searched once per API call"""
        utils = self.webhook_utils._with_lookup_memo()
        args = ([("name", "in", ["Webhook Tag A"])],)
        found = utils._call_field_search_cache(self.Tag, *args)
        self.assertEqual(found, self.tag_a)
        with patch.object(type(self.Tag), "search") as search:
            self.assertEqual(utils._call_field_search_cache(self.Tag, *args), found)
        search.assert_not_called()

    def test_14_lookup_company_scope(self):
        """check_company fields are looked up like Odoo scopes them: in the
        payload company or env.company, shared records included"""
        Partner = self.env["res.partner"]
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Company B"})
        partner_a, partner_b = Partner.create(
            [
                {"name": "Per Company", "company_id": company_a.id},
                {"name": "Per Company", "company_id": company_b.id},
            ]
        )
        shared = Partner.create({"name": "Shared Partner", "company_id": False})
        finalize = self.webhook_utils._finalize_data_to_write
        rec = self.Record

        def lookup(name, **vals):
            return finalize(rec, {"partner_id": {"name": name}, **vals})

        self.assertEqual(lookup("Per Company")["partner_id"], partner_a.id)
        # company_id given as a lookup is resolved first
        for company in (company_b.id, {"name": "Company B"}):
            res = lookup("Per Company", company_id=company)
            self.assertEqual(res["partner_id"], partner_b.id)
        # Shared records are found in any company
        self.assertEqual(lookup("Shared Partner")["partner_id"], shared.id)
        res = lookup("Shared Partner", company_id=company_b.id)
        self.assertEqual(res["partner_id"], shared.id)
        # An id is not company scoped
        res = finalize(rec, {"partner_id": {"id": partner_b.id}})
        self.assertEqual(res["partner_id"], partner_b.id)
        # Fields without check_company are not scoped
        line = self.env["webhook.test.line"]
        tag = self.Tag.create({"name": "No Company Tag"})
        res = finalize(line, {"tag_id": {"name": "No Company Tag"}})
        self.assertEqual(res["tag_id"], tag.id)
        # One2many lines are scoped on the company of their parent
        vals = self.webhook_utils._prepare_write_vals(
            rec,
            {
                "company_id": company_b.id,
                "line_ids": [{"partner_id": {"name": "Per Company"}}],
            },
            {},
        )
        self.assertEqual(vals["line_ids"][0][2]["partner_id"], partner_b.id)

    def test_15_search_data_2many_batched(self):
        """Related records of all rows are read in one query, per row result kept"""
        tag_a, tag_b = self.tag_a, self.tag_b
        self.Record.create(
            [
                {
                    "name": "Batch",
                    "tag_id": tag.id,
                    "reference": f"{tag._name},{tag.id}" if tag else False,
                }
                for tag in (tag_a, tag_b, tag_a, self.Tag)
            ]
        )
        vals = {
            "payload": {
                "search_field": ["tag_id{name}", "reference{name}"],
                "search_domain": "[('name', '=', 'Batch')]",
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
            result = self.webhook_utils.search_data(RECORD, vals)
        # One query per field, not one per row
        self.assertEqual(update_child.call_count, 2)
        expected = [
            [{"id": tag_a.id, "name": tag_a.name}],
            [{"id": tag_b.id, "name": tag_b.name}],
            [{"id": tag_a.id, "name": tag_a.name}],
            [],
        ]
        rows = result["result"]
        self.assertEqual([row["tag_id"] for row in rows], expected)
        self.assertEqual([row["reference"] for row in rows], expected)
        # Empty spec keeps the value as read
        vals["payload"]["search_field"] = ["tag_id{}"]
        result = self.webhook_utils.search_data(RECORD, vals)
        self.assertEqual(result["result"][0]["tag_id"], (tag_a.id, tag_a.name))

    def test_16_update_data_recreates_lines(self):
        """update_data replaces one2many lines, lookups after unlink still work"""
        record = self.Record.create(
            {"name": "With Lines", "line_ids": [(0, 0, {"name": "Old"})]}
        )
        vals = {
            "search_key": {"id": record.id},
            "payload": {
                "line_ids": [{"name": "New", "tag_id": {"name": "Webhook Tag B"}}],
            },
        }
        self.webhook_utils.update_data(RECORD, vals)
        self.assertEqual(record.line_ids.mapped("name"), ["New"])
        self.assertEqual(record.line_ids.tag_id, self.tag_b)

    def test_17_create_update_data(self):
        """create_update_data updates a match, or creates a new record"""
        vals = {
            "search_key": {"name": "Common Test"},
            "payload": {"amount": 5},
        }
        result = self.webhook_utils.create_update_data(RECORD, vals)
        self.assertEqual(result["result"]["id"], [self.record.id])
        self.assertEqual(self.record.amount, 5)
        vals = {
            "search_key": {"name": "Not Found"},
            "payload": {"name": "Not Found", "amount": 7},
        }
        result = self.webhook_utils.create_update_data(RECORD, vals)
        record = self.Record.browse(result["result"]["id"])
        self.assertEqual(record.amount, 7)

    def test_18_many2one_lookup_errors(self):
        """Ambiguous or missing many2one lookups raise a clear error"""
        self.Tag.create({"name": "Webhook Tag A"})
        rec = self.Record.new()
        with self.assertRaisesRegex(ValidationError, "matched more than 1 record"):
            self.webhook_utils._finalize_data_to_write(
                rec, {"tag_id": {"name": "Webhook Tag A"}}
            )
        with self.assertRaisesRegex(ValidationError, "found no match"):
            self.webhook_utils._finalize_data_to_write(
                rec, {"tag_id": {"name": "No Such Tag"}}
            )

    def test_19_create_data_result_field_subfields(self):
        """result_field accepts the search_data field{sub} syntax, values are
        returned in records only"""
        vals = {
            "payload": {
                "name": "Result Field",
                "tag_id": {"name": "Webhook Tag A"},
                "line_ids": [{"name": "L1", "tag_id": {"name": "Webhook Tag B"}}],
            },
            "result_field": ["name", "tag_id{name}", "line_ids{name,tag_id{name}}"],
        }
        result = self.webhook_utils.create_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        record = self.Record.browse(result["result"]["id"])
        tag_a = [{"id": self.tag_a.id, "name": self.tag_a.name}]
        tag_b = [{"id": self.tag_b.id, "name": self.tag_b.name}]
        expected = {
            "id": record.id,
            "name": "Result Field",
            "tag_id": tag_a,
            "line_ids": [{"id": record.line_ids.id, "name": "L1", "tag_id": tag_b}],
        }
        self.assertEqual(result["records"], [expected])
        self.assertEqual(result["result"], {"id": record.id})
        json.dumps(result, default=json_default)

    def test_20_update_data_result_field_records(self):
        """update_data returns the values after write of every updated record,
        related records read once for all of them"""
        records = self.Record.create(
            [{"name": "Many", "tag_id": tag.id} for tag in (self.tag_a, self.tag_b)]
        )
        vals = {
            "search_key": {"name": "Many"},
            "payload": {"amount": 3},
            "result_field": ["amount", "tag_id{name}"],
        }
        Utils = type(self.webhook_utils)
        with patch.object(
            Utils,
            "_update_child_2many",
            autospec=True,
            side_effect=Utils._update_child_2many,
        ) as update_child:
            result = self.webhook_utils.update_data(RECORD, vals)
        self.assertEqual(update_child.call_count, 1)
        self.assertTrue(result["is_success"])
        # result is unchanged: updated ids and echoed search_key
        self.assertEqual(result["result"], {"id": records.ids, "name": "Many"})
        self.assertEqual(
            result["records"],
            [
                {
                    "id": rec.id,
                    "amount": 3,
                    "tag_id": [{"id": rec.tag_id.id, "name": rec.tag_id.name}],
                }
                for rec in records
            ],
        )
        # No match: success with an empty list
        vals["search_key"] = {"name": "No Match"}
        result = self.webhook_utils.update_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        self.assertEqual(result["records"], [])
        # Without result_field the answer is as before
        del vals["result_field"]
        result = self.webhook_utils.update_data(RECORD, vals)
        self.assertNotIn("records", result)

    def test_21_create_update_data_result_field(self):
        """Both create_update_data branches return records"""
        vals = {
            "search_key": {"name": "Upsert"},
            "payload": {"name": "Upsert", "amount": 1},
            "result_field": ["amount"],
        }
        created = self.webhook_utils.create_update_data(RECORD, vals)
        record_id = created["result"]["id"]
        self.assertEqual(created["records"], [{"id": record_id, "amount": 1}])
        vals["payload"]["amount"] = 2
        updated = self.webhook_utils.create_update_data(RECORD, vals)
        self.assertEqual(updated["result"]["id"], [record_id])
        self.assertEqual(updated["records"], [{"id": record_id, "amount": 2}])

    def test_22_invalid_result_field_writes_nothing(self):
        """An unreadable result_field fails the call before any write"""
        cases = [
            (["nme"], "nme"),
            (["tag_id{nme}"], "tag_id.nme"),
            (["line_ids{tag_id{nme}}"], "line_ids.tag_id.nme"),
            (["name{id}"], "name (not relational)"),
            (["tag_id{name"], "tag_id{name"),
            (["tag_id{name}x"], "tag_id{name}x"),
            (["tag_id{name}}"], "tag_id{name}}"),
            ([1], "1"),
            ("name", "name"),
        ]
        for result_field, path in cases:
            with self.subTest(result_field=result_field):
                vals = {
                    "payload": {"name": "Not Created"},
                    "result_field": result_field,
                }
                result = self.webhook_utils.create_data(RECORD, vals)
                self.assertFalse(result["is_success"])
                self.assertIn(path, result["messages"])
                vals["search_key"] = {"id": self.record.id}
                result = self.webhook_utils.update_data(RECORD, vals)
                self.assertFalse(result["is_success"])
        self.assertFalse(self.Record.search([("name", "=", "Not Created")]))
        self.assertEqual(self.record.name, "Common Test")
        check = self.webhook_utils._check_result_field
        # Any depth; a reference field cannot be checked further, its model
        # is not fixed
        for result_field in (["line_ids{tag_id{parent_id{name}}}"], ["reference{x}"]):
            self.assertIsNone(check(RECORD, {"result_field": result_field}))

    def test_23_update_data_lines_on_many_records(self):
        """One2many lines are replaced on every matched record"""
        records = self.Record.create(
            [
                {"name": "Many Lines", "line_ids": [Command.create({"name": "Old"})]}
                for _i in range(2)
            ]
        )
        vals = {
            "search_key": {"name": "Many Lines"},
            "payload": {"line_ids": [{"name": "New"}]},
        }
        result = self.webhook_utils.update_data(RECORD, vals)
        self.assertTrue(result["is_success"])
        for record in records:
            self.assertEqual(record.line_ids.mapped("name"), ["New"])

    def test_24_result_field_any_depth(self):
        """Sub fields are expanded at any depth, related records keep their
        model order"""
        parent = self.Tag.create({"name": "Parent Tag"})
        self.tag_b.parent_id = parent
        vals = {
            "payload": {
                "name": "Deep",
                "line_ids": [
                    {"name": "L1", "tag_id": {"name": "Webhook Tag B"}},
                    {"name": "L2", "tag_id": {"name": "Webhook Tag A"}},
                ],
            },
            # A field given twice keeps its last spec
            "result_field": ["line_ids{id}", "line_ids{name,tag_id{parent_id{name}}}"],
        }
        result = self.webhook_utils.create_data(RECORD, vals)
        lines = self.Record.browse(result["result"]["id"]).line_ids
        parent_b = [{"id": parent.id, "name": "Parent Tag"}]
        self.assertEqual(
            result["records"][0]["line_ids"],
            [
                {
                    "id": lines[0].id,
                    "name": "L1",
                    "tag_id": [{"id": self.tag_b.id, "parent_id": parent_b}],
                },
                {
                    "id": lines[1].id,
                    "name": "L2",
                    "tag_id": [{"id": self.tag_a.id, "parent_id": []}],
                },
            ],
        )

    def test_25_auto_create_duplicates_detected(self):
        """A lookup still matching several records after auto_create fails"""
        vals = {
            "payload": {"name": "Dup", "tag_id": {"name": "Twice"}},
            "auto_create": {"tag_id": [{"name": "Twice"}, {"name": "Twice"}]},
        }
        with self.assertRaisesRegex(ValidationError, "matched more than 1 record"):
            self.webhook_utils.create_data(RECORD, vals)

    def test_26_lookup_with_several_fields(self):
        """A lookup may give several fields, all must match"""
        sale_tax, purchase_tax = self.Tag.create(
            [
                {"name": "VAT 7%", "color": 1},
                {"name": "VAT 7%", "color": 2},
            ]
        )
        finalize = self.webhook_utils._finalize_data_to_write
        res = finalize(self.Record, {"tag_id": {"name": "VAT 7%", "color": 2}})
        self.assertEqual(res["tag_id"], purchase_tax.id)
        res = finalize(
            self.Record,
            {
                "tag_ids": {
                    "records": [
                        {"name": "VAT 7%", "color": 1},
                        {"name": "Webhook Tag A"},
                        {"id": self.tag_b.id},
                    ]
                }
            },
        )
        self.assertEqual(
            res["tag_ids"], [Command.set([sale_tax.id, self.tag_a.id, self.tag_b.id])]
        )
        with self.assertRaisesRegex(ValidationError, "add a field to the lookup"):
            finalize(self.Record, {"tag_id": {"name": "VAT 7%"}})

    def test_27_many2many_every_item_must_match(self):
        """Each many2many item matches exactly one record: a missing or an
        ambiguous item fails, instead of being skipped or linking several"""
        self.Tag.create([{"name": "Twin"}, {"name": "Twin"}])
        finalize = self.webhook_utils._finalize_data_to_write
        cases = [
            (
                [{"name": "Webhook Tag A"}, {"name": "Missing Tag"}],
                '{"name": "Missing Tag"} found no match',
            ),
            ([{"name": "Twin"}], "matched more than 1 record"),
            (["Webhook Tag A"], "must be a dict"),
            # Not rounded to another id
            ([{"id": self.tag_a.id + 0.5}], "found no match"),
            ([{}], "must be a dict"),
        ]
        for records, error in cases:
            with (
                self.subTest(records=records),
                self.assertRaisesRegex(ValidationError, error),
            ):
                finalize(self.Record, {"tag_ids": {"records": records}})
        # A missing item is auto created, the others are kept
        res = finalize(
            self.Record,
            {
                "tag_ids": {
                    "mode": "add",
                    "records": [{"name": "Webhook Tag A"}, {"name": "New Tag"}],
                }
            },
            {"tag_ids": {"name": "New Tag"}},
        )
        new_tag = self.Tag.search([("name", "=", "New Tag")])
        self.assertEqual(
            res["tag_ids"], [Command.link(self.tag_a.id), Command.link(new_tag.id)]
        )
        # Same item twice is linked once, an empty list clears
        res = finalize(
            self.Record,
            {
                "tag_ids": {
                    "records": [{"name": "Webhook Tag A"}, {"name": "Webhook Tag A"}]
                }
            },
        )
        self.assertEqual(res["tag_ids"], [Command.set([self.tag_a.id])])
        res = finalize(self.Record, {"tag_ids": {"records": []}})
        self.assertEqual(res["tag_ids"], [Command.set([])])

    def test_28_many2many_lookups_batched(self):
        """Items with one field are searched together: one query per field"""
        Tag = type(self.Tag)
        # Values are converted as for the database: "id" given as a string
        items = [
            {"name": "Webhook Tag A"},
            {"name": "Webhook Tag B"},
            {"id": str(self.tag_a.id)},
            # Searched alone: field search method, list, empty string
            {"display_name": "Webhook Tag B"},
            {"name": ["Webhook Tag A"]},
        ]
        with patch.object(
            Tag, "search", autospec=True, side_effect=Tag.search
        ) as search:
            res = self.webhook_utils._with_lookup_memo()._finalize_data_to_write(
                self.Record, {"tag_ids": {"records": items}}
            )
        # name and id batched, the 2 others alone
        self.assertEqual(search.call_count, 4)
        self.assertEqual(res["tag_ids"], [Command.set([self.tag_a.id, self.tag_b.id])])
