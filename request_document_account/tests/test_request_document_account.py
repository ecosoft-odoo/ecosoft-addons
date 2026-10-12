# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestRequestDocumentAccount(AccountTestInvoicingCommon):
    def _request_bill(self):
        request = self.env["request.order"].create(
            {
                "line_ids": [Command.create({"request_type": "vendor_bill"})],
            }
        )
        action = request.line_ids.open_request_document()
        with Form(self.env["account.move"].with_context(**action["context"])) as form:
            form.partner_id = self.partner_a
            form.invoice_date = "2026-01-15"
            with form.invoice_line_ids.new() as line:
                line.name = "Requested service"
                line.account_id = self.company_data["default_account_expense"]
                line.price_unit = 100
                line.tax_ids.clear()
        return request, form.record

    def test_draft_bill_workflow(self):
        request, bill = self._request_bill()
        self.assertEqual(bill.request_document_id, request.line_ids)
        self.assertEqual(request.total_amount_document, 100)
        bill.invoice_line_ids.price_unit = 150
        self.assertEqual(request.total_amount_document, 150)
        request.action_submit()
        self.assertEqual(request.total_amount_request, 150)
        for operation in (
            lambda: bill.write({"ref": "changed"}),
            lambda: bill.invoice_line_ids.write({"price_unit": 999}),
            lambda: bill.invoice_line_ids.unlink(),
            lambda: bill.unlink(),
            lambda: bill.action_post(),
        ):
            with self.assertRaises(UserError), self.cr.savepoint():
                operation()
        request.action_approve()
        request.action_process_document()
        self.assertEqual(request.state, "done")
        self.assertEqual(bill.state, "draft")
        self.assertEqual(request.vendor_bill_count, 1)
        self.assertEqual(
            request.action_open_vendor_bills()["domain"], [("id", "in", bill.ids)]
        )
        bill.invoice_line_ids.price_unit = 175
        self.assertEqual(request.total_amount_request, 150)
        self.assertEqual(request.total_amount_document, 175)
        bill.action_post()
        self.assertEqual(bill.state, "posted")

    def test_post_bill_workflow(self):
        request, bill = self._request_bill()
        request.company_id.request_document_bill_state = "posted"
        with self.assertRaises(UserError):
            request.action_process_document()
        request.action_submit()
        request.action_approve()
        request.action_process_document()
        self.assertEqual(bill.state, "posted")
        self.assertEqual(request.state, "done")
        with self.assertRaises(UserError):
            request.action_process_document()

    def test_missing_bill_and_premature_post(self):
        request, bill = self._request_bill()
        with self.assertRaises(UserError):
            bill.action_post()
        bill.unlink()
        with self.assertRaises(UserError):
            request.action_submit()

    def test_link_validation_and_deletion(self):
        request, bill = self._request_bill()
        with self.assertRaises(UserError):
            request.unlink()
        other_bill = self.init_invoice("in_invoice", amounts=[20], taxes=[])
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            other_bill.request_document_id = request.line_ids
            self.env.flush_all()
        invoice = self.init_invoice("out_invoice", amounts=[20], taxes=[])
        bill.request_document_id = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice.request_document_id = request.line_ids
        request.unlink()
        self.assertTrue(bill.exists())

    def test_reset_to_draft_allows_edit(self):
        request, bill = self._request_bill()
        request.action_submit()
        request.action_draft()
        bill.invoice_line_ids.price_unit = 200
        request.action_submit()
        self.assertEqual(request.total_amount_request, 200)

    def test_foreign_currency(self):
        request, bill = self._request_bill()
        currency = self.env["res.currency"].create(
            {
                "name": "XRD",
                "symbol": "R",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create(
                        {
                            "name": "2026-01-01",
                            "rate": 2,
                            "company_id": request.company_id.id,
                        }
                    )
                ],
            }
        )
        bill.currency_id = currency
        expected = currency._convert(
            100, request.currency_id, request.company_id, bill.date
        )
        self.assertEqual(bill.amount_total, 100)
        self.assertEqual(request.total_amount_document, expected)
        request.action_submit()
        self.assertEqual(request.total_amount_request, expected)

    def test_accounting_permissions(self):
        request, bill = self._request_bill()
        user = new_test_user(self.env, login="request_only", groups="base.group_user")
        with self.assertRaises(AccessError):
            bill.with_user(user).write({"ref": "No accounting access"})
        request.company_id.request_document_bill_state = "posted"
        request.action_submit()
        request.action_approve()
        with self.assertRaises(AccessError):
            request.with_user(user).action_process_document()
        self.assertEqual(request.state, "approve")
        self.assertEqual(bill.state, "draft")

    def test_posting_failure_rolls_back_request(self):
        request, bill = self._request_bill()
        bill.invoice_date = False
        request.company_id.request_document_bill_state = "posted"
        request.action_submit()
        request.action_approve()
        with self.assertRaises(UserError):
            request.action_process_document()
        self.assertEqual(request.state, "approve")
        self.assertEqual(bill.state, "draft")
