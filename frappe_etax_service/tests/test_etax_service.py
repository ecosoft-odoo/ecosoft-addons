# Copyright 2025 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestETax(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.vat = "0000000000000"
        cls.tivc01 = cls.env.ref("frappe_etax_service.etax_purpose_code_01")

        doctype_code_380 = cls.env.ref("frappe_etax_service.etax_doctype_code_380")
        doctype_code_T02 = cls.env.ref("frappe_etax_service.etax_doctype_code_T02")
        doctype_code_80 = cls.env.ref("frappe_etax_service.etax_doctype_code_80")
        doctype_code_81 = cls.env.ref("frappe_etax_service.etax_doctype_code_81")

        cls.doctype_380 = cls.env["etax.doctype"].create(
            {
                "name": "ใบแจ้งหนี้ (Test)",
                "move_type": "out_invoice",
                "doctype_code_id": doctype_code_380.id,
            }
        )
        cls.doctype_T02 = cls.env["etax.doctype"].create(
            {
                "name": "ใบแจ้งหนี้/ใบกำกับภาษี (Test)",
                "move_type": "out_invoice",
                "doctype_code_id": doctype_code_T02.id,
            }
        )
        cls.doctype_80 = cls.env["etax.doctype"].create(
            {
                "name": "ใบเพิ่มหนี้ (Test)",
                "move_type": "out_invoice_debit",
                "doctype_code_id": doctype_code_80.id,
            }
        )
        cls.doctype_81 = cls.env["etax.doctype"].create(
            {
                "name": "ใบลดหนี้ (Test)",
                "move_type": "out_refund",
                "doctype_code_id": doctype_code_81.id,
            }
        )

        cls.cust_invoice = cls.init_invoice(
            "out_invoice",
            partner=cls.env.ref("base.res_partner_2"),
            amounts=[100.0],
            taxes=[cls.tax_sale_a],
        )

    def _simulate_sign_success(self, move):
        """Simulate API success by calling _hook_update_data directly."""
        move._hook_update_data(
            move._etax_sign_api_code,
            {"message": {"status": "success", "transaction_code": "TX-TEST-001"}},
        )

    def _sign_via_wizard(self, invoice, doctype):
        """Create etax.doctype.wizard and sign, with action_call_api mocked."""
        wizard = (
            self.env["etax.doctype.wizard"]
            .with_context(
                active_model="account.move",
                active_ids=invoice.ids,
                active_id=invoice.id,
            )
            .create({"etax_doctype_id": doctype.id})
        )

        def mock_action_call_api(move, code_api):
            self._simulate_sign_success(move)

        with patch.object(type(invoice), "action_call_api", mock_action_call_api):
            wizard.sign_etax_invoice()

    def test_01_purpose_code_etax(self):
        # display_name must follow {code} - {name} format
        self.assertEqual(
            self.tivc01.display_name, f"{self.tivc01.code} - {self.tivc01.name}"
        )

    def test_02_customer_invoice_etax(self):
        self.assertEqual(self.cust_invoice.state, "draft")
        self.cust_invoice.action_post()
        self.assertEqual(self.cust_invoice.state, "posted")

    def test_03_sign_invoice(self):
        """Sign ใบแจ้งหนี้ (doctype 380)"""
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[200.0],
            taxes=[self.tax_sale_a],
        )
        invoice.action_post()

        self._sign_via_wizard(invoice, self.doctype_380)

        self.assertEqual(invoice.etax_doctype_id, self.doctype_380)
        self.assertEqual(invoice.etax_doctype_id.doctype_code_id.code, "380")
        self.assertEqual(invoice.etax_status, "success")

    def test_04_sign_invoice_tax_invoice(self):
        """Sign ใบแจ้งหนี้/ใบกำกับภาษี (doctype T02)"""
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[300.0],
            taxes=[self.tax_sale_a],
        )
        invoice.action_post()

        self._sign_via_wizard(invoice, self.doctype_T02)

        self.assertEqual(invoice.etax_doctype_id, self.doctype_T02)
        self.assertEqual(invoice.etax_doctype_id.doctype_code_id.code, "T02")
        self.assertEqual(invoice.etax_status, "success")

    def test_05_replacement_sign_invoice(self):
        """Replacement sign invoice - สร้าง replacement จากใบที่ sign ไปแล้ว"""
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[400.0],
            taxes=[self.tax_sale_a],
        )
        invoice.action_post()
        # Simulate already-signed invoice
        invoice.write(
            {"etax_doctype_id": self.doctype_380.id, "etax_status": "success"}
        )

        replacement = invoice.create_replacement_etax()

        # Original must be cancelled; replacement must reference it
        self.assertEqual(invoice.state, "cancel")
        self.assertEqual(replacement.replaced_entry_id, invoice)
        self.assertEqual(replacement.etax_doctype_id, self.doctype_380)

        # Post and sign replacement
        replacement.action_post()
        self._simulate_sign_success(replacement)

        # Replacement signed; original marked as replaced
        self.assertEqual(replacement.etax_status, "success")
        self.assertEqual(invoice.etax_status, "replace")

    def test_06_sign_debit_note(self):
        """Sign ใบเพิ่มหนี้ (doctype 80)"""
        source_invoice = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[500.0],
            taxes=[self.tax_sale_a],
        )
        source_invoice.action_post()

        debit_note = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[100.0],
            taxes=[self.tax_sale_a],
        )
        debit_note.write({"debit_origin_id": source_invoice.id})
        debit_note.action_post()

        self._sign_via_wizard(debit_note, self.doctype_80)

        self.assertEqual(debit_note.etax_doctype_id, self.doctype_80)
        self.assertEqual(debit_note.etax_doctype_id.doctype_code_id.code, "80")
        self.assertEqual(debit_note.etax_status, "success")

    def test_07_sign_credit_note(self):
        """Sign ใบลดหนี้ (doctype 81)"""
        source_invoice = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[500.0],
            taxes=[self.tax_sale_a],
        )
        source_invoice.action_post()

        credit_note = self.init_invoice(
            "out_refund",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[100.0],
            taxes=[self.tax_sale_a],
        )
        credit_note.write({"reversed_entry_id": source_invoice.id})
        credit_note.action_post()

        self._sign_via_wizard(credit_note, self.doctype_81)

        self.assertEqual(credit_note.etax_doctype_id, self.doctype_81)
        self.assertEqual(credit_note.etax_doctype_id.doctype_code_id.code, "81")
        self.assertEqual(credit_note.etax_status, "success")
