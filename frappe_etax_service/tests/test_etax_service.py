# Copyright 2025 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from unittest.mock import MagicMock, patch

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.frappe_etax_service.models.etax_service import (
    FRAPPE_ETAX_STATUS_FIELDS,
    ETaxServiceMixin,
)

REQUESTS_PATH = "odoo.addons.usability_api_connector.models.common_base_api.requests"


class TestFrappeEtaxConnection(TransactionCase):
    def test_connection_normalizes_server_url(self):
        connection = self.env["frappe.etax.connection"].create(
            {
                "name": "Normalized Connection",
                "server_url": " https://etax.example.com/ ",
                "auth_token": "api-key:api-secret",
            }
        )

        self.assertEqual(connection.server_url, "https://etax.example.com")

    def test_connection_validates_url_and_token(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["frappe.etax.connection"].create(
                {
                    "name": "Invalid URL",
                    "server_url": "etax.example.com",
                    "auth_token": "api-key:api-secret",
                }
            )
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["frappe.etax.connection"].create(
                {
                    "name": "Invalid Token",
                    "server_url": "https://etax.example.com",
                    "auth_token": "missing-secret-separator",
                }
            )

    def test_company_rejects_connection_from_other_company(self):
        company = self.env["res.company"].create({"name": "e-Tax Company"})
        other_company = self.env["res.company"].create({"name": "Other Company"})
        connection = self.env["frappe.etax.connection"].create(
            {
                "name": "Other Company Connection",
                "company_id": other_company.id,
                "server_url": "https://etax.example.com",
                "auth_token": "api-key:api-secret",
            }
        )

        company.is_etax_configured = True
        self.assertTrue(company.is_etax_configured)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            company.frappe_etax_connection_id = connection

    def test_settings_can_enable_etax_before_connection(self):
        company = self.env["res.company"].create({"name": "Unconfigured e-Tax Company"})

        self.env["res.config.settings"].create(
            {
                "company_id": company.id,
                "is_etax_configured": True,
            }
        )

        self.assertTrue(company.is_etax_configured)
        self.assertFalse(company.frappe_etax_connection_id)

    def test_api_operation_uses_company_connection(self):
        connection = self.env["frappe.etax.connection"].create(
            {
                "name": "API Test Connection",
                "server_url": "https://etax.example.com/",
                "auth_token": "test-key:test-secret",
            }
        )
        self.env.company.write(
            {
                "frappe_etax_connection_id": connection.id,
                "is_etax_configured": True,
            }
        )
        api_config = self.env.ref("frappe_etax_service.api_etax_invoice_frappe")
        invoice = self.env["account.move"].new(
            {
                "move_type": "out_invoice",
                "company_id": self.env.company.id,
            }
        )
        response = MagicMock()

        self.assertFalse(api_config.endpoint_url)
        self.assertFalse(api_config.auth_required)
        self.assertFalse(api_config.auth_token)

        with patch(f"{REQUESTS_PATH}.request", return_value=response) as request:
            result = invoice._execute_rest_api(
                api_config,
                False,
                payload={"doc_data": {"value": 1}},
            )

        self.assertEqual(result, response)
        request.assert_called_once_with(
            method="POST",
            url=(
                "https://etax.example.com/"
                "api/method/etax_inet.api.etax.sign_etax_document"
            ),
            headers={"Authorization": "token test-key:test-secret"},
            timeout=30,
            data={"doc_data": '{"value": 1}'},
        )


class TestPaymentETaxValidation(TransactionCase):
    def _new_payment(self):
        return self.env["account.payment"].new(
            {
                "amount": 100.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.env.company.partner_id.id,
            }
        )

    def _validate_payment_lines(self, payment):
        with patch.object(
            ETaxServiceMixin,
            "_pre_etax_validate",
            return_value=None,
        ):
            return payment._pre_etax_validate()

    def test_payment_without_lines_is_rejected(self):
        payment = self._new_payment()

        with self.assertRaisesRegex(ValidationError, "no e-Tax line items found"):
            self._validate_payment_lines(payment)

    def test_payment_with_reconciled_invoice_lines_is_allowed(self):
        payment = self._new_payment()
        invoice = self.env["account.move"].new(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        payment.reconciled_invoice_ids = invoice

        self.assertIsNone(self._validate_payment_lines(payment))

    def test_payment_with_tax_invoice_is_allowed(self):
        payment = self._new_payment()
        payment.tax_invoice_ids = self.env["account.move.tax.invoice"].new({})

        self.assertIsNone(self._validate_payment_lines(payment))


@tagged("post_install", "-at_install")
class TestETax(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.frappe_connection = cls.env["frappe.etax.connection"].create(
            {
                "name": "Test Frappe Connection",
                "server_url": "https://etax.example.com/",
                "auth_token": "test-key:test-secret",
            }
        )
        cls.env.company.write(
            {
                "frappe_etax_connection_id": cls.frappe_connection.id,
                "is_etax_configured": True,
            }
        )
        cls.env.company.vat = "0000000000000"
        cls.tivc01 = cls.env.ref("frappe_etax_service.etax_purpose_code_01")

        doctype_code_380 = cls.env.ref("frappe_etax_service.etax_doctype_code_380")
        doctype_code_T01 = cls.env.ref("frappe_etax_service.etax_doctype_code_T01")
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
        cls.doctype_T01 = cls.env["etax.doctype"].create(
            {
                "name": "ใบรับ (Test)",
                "move_type": "entry",
                "doctype_code_id": doctype_code_T01.id,
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

    def _create_signed_reconciled_payment(self, partner=None):
        partner = partner or self.env.ref("base.res_partner_2")
        payment_date = fields.Date.today()
        invoice = self.init_invoice(
            "out_invoice",
            partner=partner,
            invoice_date=payment_date,
            amounts=[100.0],
            taxes=[],
            post=True,
        )
        payment = self.init_payment(
            100.0,
            partner=partner,
            date=payment_date,
            post=True,
        )
        payment.action_validate()
        lines = (invoice.line_ids | payment.move_id.line_ids).filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled
        )
        lines.reconcile()
        payment.write(
            {
                "etax_doctype_id": self.doctype_T01.id,
                "etax_status": "success",
            }
        )
        return invoice, payment

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

    def test_05b_payment_replacement_reconciles_on_confirm(self):
        invoice, payment = self._create_signed_reconciled_payment()
        purpose = self.env.ref("frappe_etax_service.etax_purpose_code_14")
        action = payment.action_open_replacement_wizard()
        wizard = (
            self.env["etax.replacement.wizard"]
            .with_context(**action["context"])
            .create(
                {
                    "purpose_code_id": purpose.id,
                    "reason": purpose.reason,
                }
            )
        )

        self.assertEqual(wizard.origin_ref, payment)
        replacement_action = wizard.create_replacement()
        replacement = self.env["account.payment"].browse(replacement_action["res_id"])

        self.assertEqual(payment.state, "canceled")
        self.assertEqual(replacement.state, "draft")
        self.assertEqual(replacement.replacement_origin_payment_id, payment)
        self.assertEqual(payment.replacement_payment_ids, replacement)
        self.assertEqual(replacement.invoice_ids, invoice)
        self.assertEqual(invoice.payment_state, "not_paid")

        replacement_date = fields.Date.add(payment.date, days=1)
        replacement.date = replacement_date
        replacement.action_post()

        self.assertEqual(replacement.date, replacement_date)
        self.assertEqual(replacement.reconciled_invoice_ids, invoice)
        self.assertEqual(invoice.payment_state, "paid")

    def test_05c_payment_replacement_rejects_another_partner(self):
        invoice, payment = self._create_signed_reconciled_payment()
        replacement = payment.create_replacement_etax()
        replacement.partner_id = self.env.ref("base.res_partner_3")

        with (
            self.assertRaisesRegex(ValidationError, "same customer or vendor"),
            self.cr.savepoint(),
        ):
            replacement.action_post()

        self.assertEqual(replacement.state, "draft")
        self.assertEqual(invoice.payment_state, "not_paid")

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

    def test_08_update_processing_document(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.env.ref("base.res_partner_2"),
            amounts=[100.0],
            taxes=[self.tax_sale_a],
        )
        invoice.write(
            {
                "etax_status": "processing",
                "etax_transaction_code": "TX-PROCESSING-001",
            }
        )
        response = MagicMock()
        response.json.return_value = {
            "data": [
                {
                    "status": "Error",
                    "transaction_code": "TX-PROCESSING-001",
                    "error_code": "ETAX-001",
                    "error_message": "Signing failed",
                }
            ]
        }

        with patch(
            "odoo.addons.frappe_etax_service.models.etax_service.requests.get",
            return_value=response,
        ) as request:
            result = invoice.update_processing_document()

        self.assertTrue(result)
        self.assertEqual(invoice.etax_status, "error")
        self.assertEqual(invoice.etax_error_code, "ETAX-001")
        self.assertEqual(invoice.etax_error_message, "Signing failed")
        response.raise_for_status.assert_called_once_with()
        request.assert_called_once_with(
            "https://etax.example.com/api/resource/INET ETax Document",
            headers={"Authorization": "token test-key:test-secret"},
            params={
                "filters": '[["transaction_code", "=", "TX-PROCESSING-001"]]',
                "fields": json.dumps(FRAPPE_ETAX_STATUS_FIELDS),
                "limit_page_length": 1,
            },
            timeout=20,
        )

    def test_09_processing_document_crons(self):
        for xmlid, model_name in (
            (
                "frappe_etax_service.ir_cron_run_update_processing_document",
                "account.move",
            ),
            (
                "frappe_etax_service.ir_cron_run_update_processing_payment",
                "account.payment",
            ),
        ):
            cron = self.env.ref(xmlid)
            self.assertEqual(cron.model_id.model, model_name)
            self.assertEqual(cron.interval_number, 1)
            self.assertEqual(cron.interval_type, "minutes")
            self.assertEqual(cron.code, "model.run_update_processing_document()")

    def test_10_processing_document_cron_respects_limit(self):
        invoices = self.env["account.move"]
        for transaction_code in ("TX-BATCH-001", "TX-BATCH-002"):
            invoice = self.init_invoice(
                "out_invoice",
                partner=self.env.ref("base.res_partner_2"),
                amounts=[100.0],
                taxes=[self.tax_sale_a],
            )
            invoice.write(
                {
                    "etax_status": "processing",
                    "etax_transaction_code": transaction_code,
                }
            )
            invoices |= invoice

        with patch.object(
            ETaxServiceMixin,
            "update_processing_document",
            return_value=True,
        ) as update:
            processed = invoices.run_update_processing_document(
                limit=1,
                auto_commit=False,
            )

        self.assertEqual(processed, 1)
        update.assert_called_once()
