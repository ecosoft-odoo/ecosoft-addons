# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestZortOrderPerformance(TransactionCase):
    """Performance regression tests for ZortOrder._create_sale_order and helpers.

    Verifies that the N+1 refactor (JSON parsed once, batch SKU lookups, batch
    pre-fetches) does not change observable behaviour.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Test-only products (genuinely new data for these tests)
        cls.product_a = cls.env["product.product"].create(
            {"name": "Product A", "default_code": "SKU-A", "type": "consu"}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Product B", "default_code": "SKU-B", "type": "consu"}
        )

        # Special products — look up the already-installed records from data XML
        cls.shipping_product = cls.env.ref(
            "zort_connector.product_shipping_fee"
        ).product_variant_id
        cls.discount_product = cls.env.ref(
            "zort_connector.product_zort_discount"
        ).product_variant_id
        cls.voucher_product = cls.env.ref(
            "zort_connector.voucher_amount_zort"
        ).product_variant_id

        # Zort product mappings
        cls.zp_a = cls.env["zort.product"].create(
            {
                "name": "Product A",
                "id_zort_product": "SKU-A",
                "product_id": cls.product_a.id,
            }
        )
        cls.zp_b = cls.env["zort.product"].create(
            {
                "name": "Product B",
                "id_zort_product": "SKU-B",
                "product_id": cls.product_b.id,
            }
        )

        # A minimal zort.order record for calling instance methods
        cls.zort_order = cls.env["zort.order"].create(
            {
                "zort_order_id": "PERF-TEST-001",
                "zort_order_number": "TEST-001",
                "zort_status": "new",
                "source_channel": "shopee",
                "raw_data": "{}",
            }
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _zort_data(self, lines=None, shipping=0.0, discount=0.0, voucher=0.0):
        """Return a minimal Zort order dict for testing."""
        if lines is None:
            lines = [
                {
                    "productid": "SKU-A",
                    "number": 2,
                    "pricepernumber": 100.0,
                    "sku": "SKU-A",
                },
                {
                    "productid": "SKU-B",
                    "number": 1,
                    "pricepernumber": 50.0,
                    "sku": "SKU-B",
                },
            ]
        return {
            "list": lines,
            "shippingamount": shipping,
            "discount": discount,
            "voucheramount": voucher,
        }

    def test_get_customers_data_accepts_zort_order_dict(self):
        """_get_customers_data must accept a pre-parsed dict."""
        zort_data = {
            "customername": "Test Customer",
            "customerphone": "0812345678",
            "customeremail": "test@example.com",
            "customeraddress": "Bangkok",
            "customerprovince": "Bangkok",
            "customerpostcode": "10400",
            "customeridnumber": "",
        }
        # Calling with a dict parameter must not raise TypeError
        try:
            self.zort_order._get_customers_data(zort_data)
        except TypeError as e:
            self.fail(f"_get_customers_data raised TypeError: {e}")

    def test_create_customer_accepts_zort_order_dict(self):
        """_create_customer must accept a pre-parsed dict (no internal json.loads)."""
        zort_data = {
            "customername": "Dict Customer",
            "customerphone": "",
            "customeremail": "",
            "customeraddress": "",
            "customerprovince": "",
            "customerpostcode": "",
            "customeridnumber": "",
        }
        partner = self.zort_order._create_customer(zort_data)
        self.assertEqual(partner.name, "Dict Customer")

    def test_prepare_sale_order_lines_accepts_zort_order_dict(self):
        """_prepare_sale_order_lines must accept a pre-parsed dict."""
        zort_data = self._zort_data()
        commands = self.zort_order._prepare_sale_order_lines(zort_data)
        self.assertEqual(len(commands), 2)  # 2 lines, no shipping/discount/voucher
