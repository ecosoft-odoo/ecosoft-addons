# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

PAPER_INVOICES = [
    ("ST6906-00049", "2026-06-09", 146240.00),
    ("IV6907-00214", "2026-07-07", 18900.00),
    ("IV6907-00215", "2026-07-07", 33100.00),
    ("IV6907-00239", "2026-07-16", 62800.00),
    ("IV6907-00240", "2026-07-16", 44800.00),
]


@tagged("post_install", "-at_install")
class TestETaxMultiReference(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connection = cls.env["frappe.etax.connection"].create(
            {
                "name": "Multi Reference Connection",
                "server_url": "https://etax.example.com",
                "auth_token": "test-key:test-secret",
                "support_multi_reference": True,
            }
        )
        cls.env.company.write(
            {
                "frappe_etax_connection_id": cls.connection.id,
                "is_etax_configured": True,
                "vat": "0000000000000",
            }
        )
        cls.partner = cls.env.ref("base.res_partner_2")
        cls.purpose = cls.env["etax.purpose.code"].search(
            [("etax_doctype_code_ids.code", "=", "81"), ("reason", "!=", False)],
            limit=1,
        )
        cls.t02 = cls.env.ref("frappe_etax_service.etax_doctype_code_T02")
        cls.doctype_t02 = cls.env["etax.doctype"].create(
            {
                "name": "ใบแจ้งหนี้/ใบกำกับภาษี (Test)",
                "move_type": "out_invoice",
                "doctype_code_id": cls.t02.id,
            }
        )
        cls.doctype_81 = cls.env["etax.doctype"].create(
            {
                "name": "ใบลดหนี้ (Test)",
                "move_type": "out_refund",
                "doctype_code_id": cls.env.ref(
                    "frappe_etax_service.etax_doctype_code_81"
                ).id,
            }
        )

    def _payload(self, move):
        config = self.env.ref("frappe_etax_service.api_etax_invoice_frappe")
        return safe_eval(
            config.python_code.strip(),
            {
                "rec": move,
                "env": self.env,
                "form_type": "frappe",
                "form_name": "Test",
                "pdf_content": False,
            },
        )["doc_data"]

    def _invoice(self, amount, date="2026-07-01"):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner,
            invoice_date=fields.Date.to_date(date),
            amounts=[amount],
            taxes=[self.tax_sale_a],
            post=True,
        )
        invoice.etax_doctype_id = self.doctype_t02
        return invoice

    def _credit_note(self, amounts, **values):
        credit_note = self.init_invoice(
            "out_refund",
            partner=self.partner,
            invoice_date=fields.Date.to_date("2026-10-07"),
            amounts=amounts,
            taxes=[self.tax_sale_a],
        )
        credit_note.write(
            {
                "create_purpose_code": self.purpose.code,
                "create_purpose": self.purpose.reason,
                **values,
            }
        )
        return credit_note

    def _paper_references(self):
        return [
            Command.create(
                {
                    "sequence": sequence,
                    "name": name,
                    "date": fields.Date.to_date(date),
                    "amount_untaxed": amount,
                }
            )
            for sequence, (name, date, amount) in enumerate(PAPER_INVOICES)
        ]

    def test_single_reversal_payload_unchanged(self):
        invoice = self._invoice(500.0)
        credit_note = self._credit_note([100.0], reversed_entry_id=invoice.id)
        data = self._payload(credit_note)
        self.assertEqual(data["ref_document_id"], invoice.name)
        self.assertEqual(data["ref_document_issue_dtm"], "2026-07-01T00:00:00")
        self.assertEqual(data["ref_document_type_code"], "T02")
        self.assertEqual(data["ref_document_name"], self.t02.name)
        self.assertNotIn("additional_ref_documents", data)
        self.assertEqual(data["original_amount_untaxed"], 500.0)
        self.assertEqual(data["final_amount_untaxed"], 400.0)
        self.assertEqual(data["adjust_amount_untaxed"], 100.0)
        self.assertEqual(data["buyer_ref_document"], "")

    def test_paper_invoices_payload(self):
        credit_note = self._credit_note(
            [7312.0, 945.0, 1655.0, 3140.0, 2240.0],
            etax_reference_ids=self._paper_references(),
        )
        data = self._payload(credit_note)
        self.assertEqual(data["ref_document_id"], "ST6906-00049")
        self.assertEqual(data["ref_document_issue_dtm"], "2026-06-09T00:00:00")
        self.assertEqual(data["ref_document_type_code"], "T02")
        self.assertEqual(data["ref_document_name"], "ใบแจ้งหนี้/ใบกำกับภาษี")
        self.assertEqual(
            [ref["ref_document_id"] for ref in data["additional_ref_documents"]],
            ["IV6907-00214", "IV6907-00215", "IV6907-00239", "IV6907-00240"],
        )
        self.assertEqual(
            data["additional_ref_documents"][0]["ref_document_issue_dtm"],
            "2026-07-07T00:00:00",
        )
        self.assertAlmostEqual(data["original_amount_untaxed"], 305840.0)
        self.assertAlmostEqual(data["final_amount_untaxed"], 290548.0)
        self.assertAlmostEqual(data["adjust_amount_untaxed"], 15292.0)
        self.assertAlmostEqual(credit_note.etax_original_amount, 305840.0)
        self.assertAlmostEqual(credit_note.etax_corrected_amount, 290548.0)

    def test_reversal_with_additional_references(self):
        origin = self._invoice(300.0)
        other = self._invoice(200.0, date="2026-07-02")
        credit_note = self._credit_note(
            [50.0],
            reversed_entry_id=origin.id,
            etax_reference_ids=[Command.create({"ref_move_id": other.id})],
        )
        reference = credit_note.etax_reference_ids
        self.assertEqual(reference.name, other.name)
        self.assertEqual(reference.date, other.invoice_date)
        self.assertEqual(reference.amount_untaxed, 200.0)
        self.assertEqual(reference.type_code_id, self.t02)
        data = self._payload(credit_note)
        self.assertEqual(data["ref_document_id"], origin.name)
        self.assertEqual(
            data["additional_ref_documents"][0]["ref_document_id"], other.name
        )
        self.assertEqual(data["original_amount_untaxed"], 500.0)
        self.assertEqual(data["final_amount_untaxed"], 450.0)

    def test_debit_note_with_additional_references(self):
        origin = self._invoice(300.0)
        debit_note = self.init_invoice(
            "out_invoice",
            partner=self.partner,
            amounts=[30.0],
            taxes=[self.tax_sale_a],
        )
        debit_note.write(
            {
                "debit_origin_id": origin.id,
                "etax_reference_ids": [
                    Command.create(
                        {
                            "name": "PAPER-1",
                            "date": "2026-06-01",
                            "amount_untaxed": 700.0,
                        }
                    )
                ],
            }
        )
        data = self._payload(debit_note)
        self.assertEqual(data["original_amount_untaxed"], 1000.0)
        self.assertEqual(data["final_amount_untaxed"], 1030.0)
        self.assertEqual(len(data["additional_ref_documents"]), 1)

    def test_duplicate_reference_rejected(self):
        origin = self._invoice(300.0)
        with self.assertRaises(ValidationError):
            self._credit_note(
                [50.0],
                reversed_entry_id=origin.id,
                etax_reference_ids=[Command.create({"ref_move_id": origin.id})],
            )
        with self.assertRaises(ValidationError):
            self._credit_note(
                [50.0],
                etax_reference_ids=[
                    Command.create(
                        {"name": "DUP", "date": "2026-06-01", "amount_untaxed": 1}
                    ),
                    Command.create(
                        {"name": "DUP", "date": "2026-06-02", "amount_untaxed": 2}
                    ),
                ],
            )

    def test_sign_validation(self):
        credit_note = self._credit_note([100.0])
        credit_note.action_post()
        with self.assertRaisesRegex(ValidationError, "at least one reference"):
            credit_note._pre_etax_validate()
        credit_note.button_draft()
        credit_note.etax_reference_ids = [
            Command.create(
                {"name": "OLD-1", "date": "2026-06-01", "amount_untaxed": 50}
            )
        ]
        credit_note.action_post()
        with self.assertRaisesRegex(ValidationError, "exceeds"):
            credit_note._pre_etax_validate()
        credit_note.button_draft()
        credit_note.etax_reference_ids.amount_untaxed = 500
        credit_note.etax_reference_ids = [
            Command.create(
                {"name": "OLD-2", "date": "2026-06-01", "amount_untaxed": 50}
            )
        ]
        credit_note.action_post()
        self.connection.support_multi_reference = False
        with self.assertRaisesRegex(ValidationError, "does not support"):
            credit_note._pre_etax_validate()
        self.connection.support_multi_reference = True
        credit_note._pre_etax_validate()

    def test_reference_locked_after_sign(self):
        credit_note = self._credit_note(
            [7312.0], etax_reference_ids=self._paper_references()
        )
        credit_note.action_post()
        credit_note.etax_status = "success"
        with self.assertRaises(ValidationError):
            credit_note.etax_reference_ids[0].name = "CHANGED"
        with self.assertRaises(ValidationError):
            credit_note.etax_reference_ids[0].unlink()

    def _wizard(self, invoices):
        return Form(
            self.env["etax.multi.credit.note.wizard"].with_context(
                active_model="account.move", active_ids=invoices.ids
            )
        )

    def test_wizard_percent_creates_credit_note(self):
        invoices = self._invoice(1000.0) | self._invoice(3000.0, date="2026-07-02")
        form = self._wizard(invoices)
        form.purpose_code_id = self.purpose
        form.credit_percent = 5.0
        wizard = form.save()
        self.assertEqual(wizard.line_ids.mapped("remaining_amount"), [1000.0, 3000.0])
        wizard.action_calculate()
        self.assertEqual(wizard.line_ids.mapped("credit_amount"), [50.0, 150.0])
        action = wizard.action_create()
        credit_note = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(credit_note.move_type, "out_refund")
        self.assertEqual(credit_note.partner_id, self.partner)
        self.assertEqual(credit_note.amount_untaxed, 200.0)
        self.assertEqual(credit_note.amount_tax, 30.0)
        self.assertEqual(credit_note.create_purpose_code, self.purpose.code)
        self.assertEqual(credit_note.etax_reference_ids.ref_move_id, invoices)
        self.assertEqual(
            credit_note.etax_reference_ids.mapped("credit_amount"), [50, 150]
        )
        self.assertEqual(credit_note.etax_original_amount, 4000.0)
        self.assertEqual(credit_note.etax_corrected_amount, 3800.0)
        self.assertEqual(
            credit_note.invoice_line_ids.etax_origin_line_id,
            invoices.invoice_line_ids,
        )
        self.assertEqual(
            invoices.invoice_line_ids.mapped("etax_credited_amount"), [50.0, 150.0]
        )
        invoices.invalidate_recordset(["etax_credited_amount"])
        self.assertEqual(invoices.mapped("etax_credited_amount"), [50.0, 150.0])

    def test_wizard_product_filter_and_total(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner,
            invoice_date=fields.Date.to_date("2026-07-01"),
            products=self.product_a | self.product_b,
            taxes=[self.tax_sale_a],
        )
        invoice.invoice_line_ids[1].tax_ids = False
        invoice.action_post()
        line_a, line_b = invoice.invoice_line_ids
        form = self._wizard(invoice)
        self.assertEqual(len(form.line_ids), 2)
        form.product_ids.add(self.product_b)
        form.credit_method = "amount"
        form.total_amount = 40.0
        wizard = form.save()
        self.assertEqual(wizard.line_ids.invoice_line_id, line_b)
        wizard.action_calculate()
        action = wizard.action_create()
        credit_line = self.env["account.move"].browse(action["res_id"]).invoice_line_ids
        self.assertEqual(credit_line.product_id, self.product_b)
        self.assertEqual(credit_line.price_subtotal, 40.0)
        self.assertFalse(credit_line.tax_ids)
        self.assertEqual(credit_line.account_id, line_b.account_id)
        self.assertEqual(credit_line.name, line_b.name)
        self.assertEqual(line_b.etax_credited_amount, 40.0)
        self.assertEqual(line_a.etax_credited_amount, 0.0)
        wizard = self._wizard(invoice).save()
        self.assertEqual(
            wizard.line_ids.mapped("remaining_amount"),
            [line_a.price_subtotal, line_b.price_subtotal - 40.0],
        )

    def test_wizard_validation(self):
        invoices = self._invoice(100.0) | self._invoice(300.0, date="2026-07-02")
        form = self._wizard(invoices)
        form.credit_method = "amount"
        form.total_amount = 150.0
        wizard = form.save()
        with self.assertRaisesRegex(UserError, "at least one line"):
            wizard.action_create()
        wizard.line_ids[0].credit_amount = 120.0
        wizard.line_ids[1].credit_amount = 30.0
        with self.assertRaisesRegex(UserError, "exceeds the remaining"):
            wizard.action_create()
        wizard.line_ids[0].credit_amount = 100.0
        wizard.line_ids[1].credit_amount = 60.0
        with self.assertRaisesRegex(UserError, "exceeds the total"):
            wizard.action_create()
        wizard.line_ids[1].credit_amount = 50.0
        wizard.action_create()

    def test_reversal_links_origin_lines(self):
        invoice = self._invoice(500.0)
        reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"journal_id": invoice.journal_id.id})
        )
        reversal.reverse_moves()
        credit_note = reversal.new_move_ids
        self.assertEqual(
            credit_note.invoice_line_ids.etax_origin_line_id,
            invoice.invoice_line_ids,
        )
        self.assertEqual(invoice.invoice_line_ids.etax_credited_amount, 500.0)
        self.assertFalse(credit_note.etax_allowed_product_ids)

    def test_manual_credit_note_products_restricted(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner,
            invoice_date=fields.Date.to_date("2026-07-01"),
            products=self.product_a,
            post=True,
        )
        credit_note = self.init_invoice(
            "out_refund", partner=self.partner, products=self.product_b
        )
        credit_note.etax_reference_ids = [Command.create({"ref_move_id": invoice.id})]
        self.assertEqual(credit_note.etax_allowed_product_ids, self.product_a)
        with self.assertRaisesRegex(UserError, "not found in the referenced"):
            credit_note.action_post()
        credit_note.invoice_line_ids.product_id = self.product_a
        credit_note.action_post()

    def test_wizard_rejects_mixed_partners(self):
        invoice = self._invoice(100.0)
        other = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        with self.assertRaisesRegex(UserError, "same customer"):
            self._wizard(invoice | other)

    def test_reversal_wizard_mixed_etax_status(self):
        signed = self._invoice(100.0)
        signed.etax_status = "success"
        unsigned = self._invoice(100.0, date="2026-07-02")
        wizard = (
            self.env["account.move.reversal"]
            .with_context(
                active_model="account.move", active_ids=(signed | unsigned).ids
            )
            .create({"journal_id": signed.journal_id.id})
        )
        self.assertFalse(wizard.etax_status)
        with self.assertRaisesRegex(UserError, "should be same"):
            wizard.reverse_moves()
