# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from xml.etree import ElementTree

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import file_open
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestETaxPayload(TransactionCase):
    def setUp(self):
        super().setUp()
        self.tax = self.env["account.tax"].create(
            {"name": "Payload VAT 7%", "amount": 7, "type_tax_use": "sale"}
        )

    def _invoice(self, entries, taxed=True, **values):
        return self.env["account.move"].new(
            dict(
                move_type="out_invoice",
                currency_id=self.env.ref("base.THB").id,
                invoice_line_ids=[
                    Command.create(
                        dict(
                            name="Payload item",
                            quantity=quantity,
                            price_unit=price,
                            tax_ids=[Command.set(self.tax.ids if taxed else [])],
                            **extra,
                        )
                    )
                    for price, quantity, extra in entries
                ],
                **values,
            )
        )

    def test_deposit_price_and_quantity_signs(self):
        for price, quantity in [(-120, 1), (120, -1)]:
            with self.subTest(price=price, quantity=quantity):
                invoice = self._invoice(
                    [(100, 1, {}), (200, 1, {}), (price, quantity, {})]
                )
                items = invoice._get_etax_line_item_information()
                self.assertEqual(len(items), 3)
                self.assertEqual(items[-1]["line_base_amount"], -120)
                self.assertEqual(items[-1]["line_tax_amount"], -8.4)
                self.assertEqual(items[-1]["line_total_amount"], -128.4)
                self.assertEqual(items[-1]["line_allowance_actual_amount"], 120)
                self.assertEqual(items[-1]["line_allowance_charge_ind"], "false")
                self.assertEqual(invoice._get_etax_final_amount_untaxed(), 180)

    def test_positive_deposit_and_exempt_lines(self):
        invoice = self._invoice([(120, 1, {})], taxed=False)
        item = invoice._get_etax_line_item_information()[0]
        self.assertEqual(item["line_base_amount"], 120)
        self.assertEqual(item["line_tax_amount"], 0)
        self.assertEqual(item["line_tax_type_code"], "FRE")
        self.assertEqual(item["line_allowance_actual_amount"], 0)
        self.assertEqual(item["product_price"], 120)

    def test_skip_and_discount(self):
        invoice = self._invoice(
            [(100, 2, {"discount": 10}), (-20, 1, {"skip_etax": True})]
        )
        items = invoice._get_etax_line_item_information()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["line_base_amount"], 180)
        self.assertEqual(items[0]["product_quantity"], 2)
        self.assertEqual(items[0]["line_allowance_charge_ind"], "false")
        self.assertEqual(items[0]["line_allowance_actual_amount"], 20)
        self.assertEqual(invoice._get_etax_final_amount_untaxed(), 180)

    def test_discount_excludes_price_included_vat(self):
        self.tax.price_include_override = "tax_included"
        invoice = self._invoice([(107, 2, {"discount": 10})])
        item = invoice._get_etax_line_item_information()[0]
        self.assertEqual(item["line_allowance_actual_amount"], 20)
        self.assertEqual(item["line_base_amount"], 180)
        self.assertEqual(item["line_tax_amount"], 12.6)
        self.assertEqual(item["line_total_amount"], 192.6)

    def test_full_discount_and_exempt_discount(self):
        for discount, allowance, base in [(10, 20, 180), (100, 200, 0)]:
            with self.subTest(discount=discount):
                invoice = self._invoice([(100, 2, {"discount": discount})], taxed=False)
                item = invoice._get_etax_line_item_information()[0]
                self.assertEqual(item["line_allowance_actual_amount"], allowance)
                self.assertEqual(item["line_allowance_charge_ind"], "false")
                self.assertEqual(item["line_base_amount"], base)
                self.assertEqual(item["product_price"], 100)
                self.assertEqual(item["product_quantity"], 2)

    def test_discounted_negative_line_is_one_allowance(self):
        invoice = self._invoice([(300, 1, {}), (-100, 1, {"discount": 10})])
        item = invoice._get_etax_line_item_information()[-1]
        self.assertEqual(item["line_allowance_actual_amount"], 90)
        self.assertEqual(item["line_base_amount"], -90)

    def test_adjustment_and_replacement_totals(self):
        origin = self._invoice([(300, 1, {})])
        credit = self._invoice([(120, 1, {})])
        # Unsaved moves have no synchronized journal items for amount_untaxed.
        origin.amount_untaxed = 300
        credit.amount_untaxed = 120
        credit.reversed_entry_id = origin
        self.assertEqual(credit._get_etax_final_amount_untaxed(), 180)
        debit = self._invoice([(120, 1, {})])
        debit.amount_untaxed = 120
        debit.debit_origin_id = origin
        self.assertEqual(debit._get_etax_final_amount_untaxed(), 420)
        replacement = self._invoice([(300, 1, {}), (-120, 1, {})])
        replacement.replaced_entry_id = origin
        self.assertEqual(replacement._get_etax_final_amount_untaxed(), 180)

    def _xml_payload(self, record, xmlid):
        # Read the shipped mapping: existing databases may retain customized
        # noupdate API configs until their administrator copies the new code.
        with file_open("frappe_etax_service/data/api_config_data.xml", "rb") as source:
            root = ElementTree.parse(source).getroot()
        code = root.find(f"record[@id='{xmlid}']/field[@name='python_code']").text
        return safe_eval(
            code.strip(),
            {
                "rec": record,
                "form_type": "odoo",
                "form_name": "Test",
                "pdf_content": "test-pdf",
            },
        )

    def test_invoice_document_mapping(self):
        invoice = self._invoice([(300, 1, {}), (-120, 1, {})])
        partner = self.env["res.partner"].new({"name": "Payload buyer"})
        invoice.partner_id = partner
        invoice.invoice_date = fields.Date.to_date("2026-09-10")
        invoice.payment_reference = "BUYER-REF"
        origin = self._invoice([(300, 1, {})])
        origin.invoice_date = fields.Date.to_date("2026-09-01")
        invoice.replaced_entry_id = origin
        invoice.name = "ETAX-NEW"
        origin.name = "ETAX-OLD"
        payload = self._xml_payload(invoice, "api_etax_invoice_frappe")
        data = payload["doc_data"]
        self.assertEqual(data["document_id"], "ETAX-NEW")
        self.assertEqual(data["document_issue_dtm"], "2026-09-10T00:00:00")
        self.assertEqual(data["ref_document_id"], "ETAX-OLD")
        self.assertEqual(data["ref_document_issue_dtm"], "2026-09-01T00:00:00")
        self.assertEqual(data["buyer_ref_document"], "BUYER-REF")
        self.assertEqual(data["buyer_name"], "Payload buyer")
        self.assertEqual(data["buyer_address_line3"], "")
        self.assertEqual(data["buyer_branch_id"], "00000")
        self.assertEqual(data["final_amount_untaxed"], 180)
        self.assertEqual(data["line_item_information"][1]["line_base_amount"], -120)
        self.assertEqual(payload["pdf_content"], "test-pdf")
        self.assertEqual(payload["form_name"], "Test")
        self.assertEqual(payload["form_type"], "odoo")

    def test_payment_and_replacement_share_document_mapping(self):
        payment = self.env["account.payment"].new({"amount": 192.6})
        payment.reconciled_invoice_ids = self._invoice([(300, 1, {}), (-120, 1, {})])
        origin = self.env["account.payment"].new(
            {"name": "RECEIPT-OLD", "date": "2026-09-01"}
        )
        payment.replacement_origin_payment_id = origin
        normal = self._xml_payload(payment, "api_etax_payment_frappe")
        replacement = self._xml_payload(payment, "api_etax_payment_replace_frappe")
        self.assertEqual(normal, replacement)
        self.assertEqual(normal["doc_data"]["ref_document_id"], "RECEIPT-OLD")
        self.assertEqual(
            normal["doc_data"]["ref_document_issue_dtm"], "2026-09-01T00:00:00"
        )
        self.assertIs(normal["doc_data"]["original_amount_untaxed"], False)
        self.assertIs(normal["doc_data"]["adjust_amount_untaxed"], False)
        self.assertTrue(normal["doc_data"]["line_item_information"])
