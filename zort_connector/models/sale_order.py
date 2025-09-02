import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "zort.api"]

    # This field can be used to store the Zort order ID
    is_zort_order = fields.Boolean(
        help="Indicates if this sale order is created from Zort.",
        default=False,
        readonly=True,
        index=True,
    )
    zort_order_id = fields.Char(
        help="The ID of the order in Zort.",
        copy=False,
        readonly=True,
        index=True,
    )
    zort_order_number = fields.Char(
        help="The order number in Zort.",
        copy=False,
        readonly=True,
        index=True,
    )
    zort_order_status = fields.Char(
        help="The status of the order in Zort.",
        copy=False,
        readonly=True,
    )
    zort_payment_status = fields.Char(
        help="The payment status of the order in Zort.",
        copy=False,
        readonly=True,
    )
    zort_order_data = fields.Json(
        help="The raw order data fetched from Zort.",
        copy=False,
        readonly=True,
    )

    @api.model
    def process_sales_order_from_zort(self, status="0", orderidlist="", numberlist=""):
        """
        Create or update sale orders in Odoo based on data from Zort.

        This method:
        - Updates existing sale orders that match Zort order IDs
        - Creates new sale orders from Zort data

        Args:
            status (str, optional): Zort order status filter for fetching new orders.
            orderidlist (str, optional): Comma-separated Zort order IDs to process.
            numberlist (str, optional): Comma-separated Zort order numbers to process.

        Returns:
            bool: True if the operation completes successfully.
        """
        # Update existing orders
        self._update_existing_zort_orders()

        # Create new orders
        self._create_new_zort_orders(status, orderidlist, numberlist)

        return True

    def _update_existing_zort_orders(self):
        """Update existing sale orders with latest data from Zort."""
        zort_ids = self._get_existing_zort_order_ids()
        res = self._get_list_order(status="", orderidlist=zort_ids)
        orders = res.get("list", [])

        for order in orders:
            try:
                so = self.search([("zort_order_id", "=", order.get("id"))], limit=1)
                if so:
                    self._update_sale_order_from_zort(so, order)
            except Exception as e:
                _logger.error("Error updating existing sale order from Zort: %s", e)

    def _update_sale_order_from_zort(self, sale_order, zort_order):
        """Update a single sale order with Zort data and handle status changes."""
        # Update order data
        sale_order.write(
            {
                "zort_order_number": zort_order.get("number"),
                "zort_order_status": zort_order.get("status"),
                "zort_payment_status": zort_order.get("paymentstatus"),
                "zort_order_data": zort_order,
            }
        )
        _logger.info("Updated Sale Order: %s", sale_order.name)

        # Handle status-based actions
        self._handle_zort_order_status(sale_order, zort_order.get("status"))

    def _handle_zort_order_status(self, sale_order, zort_status):
        """Handle order workflow based on Zort order status."""
        if zort_status == "Voided":
            sale_order.action_cancel()
        elif zort_status == "Waiting" and sale_order.state not in ["sale", "cancel"]:
            sale_order.action_confirm()
        elif zort_status == "Success":
            self._process_success_order(sale_order)

    def _process_success_order(self, sale_order):
        """Process order when Zort status is 'Success'."""
        # Confirm order if not already confirmed
        if sale_order.state not in ["sale", "cancel"]:
            sale_order.action_confirm()

        # Validate deliveries
        for picking in sale_order.picking_ids:
            if picking.state not in ["done", "cancel"]:
                picking.button_validate()
        _logger.info("Delivery order done for Sale Order: %s", sale_order.name)

        # Force recomputation of delivered quantities
        sale_order.order_line.invalidate_recordset(["qty_delivered"])
        sale_order.order_line._compute_qty_delivered()

        # Create draft invoice
        self._create_draft_invoice(sale_order)

    def _create_draft_invoice(self, sale_order):
        """Create draft invoice for the sale order."""
        invoice_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=sale_order.ids, active_id=sale_order.id)
            .create({"advance_payment_method": "delivered"})
        )
        invoice_wizard.create_invoices()
        _logger.info("Draft invoice created for Sale Order: %s", sale_order.name)

    def _create_new_zort_orders(self, status, orderidlist, numberlist):
        """Create new sale orders from Zort data."""
        _logger.info("Creating Sale Order from Zort...")

        zort_ids = [
            int(id)
            for id in self._get_existing_zort_order_ids().split(",")
            if id.strip()
        ]
        res = self._get_list_order(
            status=status, orderidlist=orderidlist, numberlist=numberlist
        )
        orders = res.get("list", [])

        for order in orders:
            try:
                if order.get("id") in zort_ids:
                    _logger.info("Zort Order already exists: %s", order.get("id"))
                    continue

                self._create_single_sale_order(order)
            except Exception as e:
                _logger.error("Error creating sale order from Zort: %s", e)

    def _create_single_sale_order(self, zort_order):
        """Create a single sale order from Zort order data."""
        # Prepare order data
        order_data = {
            "partner_id": self._get_marketplace_customer(zort_order),
            "is_zort_order": True,
            "zort_order_id": zort_order.get("id"),
            "zort_order_number": zort_order.get("number"),
            "zort_order_status": zort_order.get("status"),
            "zort_payment_status": zort_order.get("paymentstatus"),
            "zort_order_data": zort_order,
        }

        # Create the sale order
        sale_order = self.create(order_data)

        # Add order lines
        order_lines = self._prepare_order_lines(zort_order)
        if order_lines:
            sale_order.order_line = order_lines

        _logger.info("Created Sale Order: %s", sale_order.name)

    def _prepare_order_lines(self, zort_order):
        """Prepare order lines from Zort order data."""
        order_lines = []

        # Add product lines
        for line in zort_order.get("list", []):
            product = self.env["product.product"].search(
                [("default_code", "=", line.get("sku"))], limit=1
            )
            if not product:
                _logger.warning(
                    "Product with SKU %s not found. Skipping line.",
                    line.get("sku"),
                )
                continue

            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": line.get("number", 1),
                        "price_unit": line.get("totalprice", 0.0),
                        "name": line.get("name", product.name),
                    },
                )
            )

        # Add shipping fee if exists
        shipping_amount = zort_order.get("shippingamount", 0.0)
        if shipping_amount > 0:
            order_lines.append(self._add_shipping_fee_line(shipping_amount))

        # Add discount if exists
        discount_amount = zort_order.get("discountamount", 0.0)
        if discount_amount > 0:
            order_lines.append(self._add_discount_line(discount_amount))

        return order_lines

    def _add_shipping_fee_line(self, shipping_amount):
        """Add a shipping fee line to the sale order."""
        shipping_fee_product = self.env["product.product"].search(
            [("default_code", "=", "shipping_fee")], limit=1
        )
        return (
            0,
            0,
            {
                "product_id": shipping_fee_product.id,
                "product_uom_qty": 1,
                "price_unit": shipping_amount,
                "name": "Shipping Fee",
            },
        )

    def _add_discount_line(self, discount_amount):
        """Add a discount line to the sale order."""
        discount_product = self.env["product.product"].search(
            [("default_code", "=", "zort_discount")], limit=1
        )
        return (
            0,
            0,
            {
                "product_id": discount_product.id,
                "product_uom_qty": 1,
                "price_unit": -discount_amount,
                "name": "Discount",
            },
        )

    def _get_existing_zort_order_ids(self):
        """
        Get existing Zort orders (id) in draft, sent, or sale state
        Return as comma-separated string Ex. "1234,5678,91011"
        """
        zort_orders = self.search(
            [("is_zort_order", "=", True), ("state", "in", ["draft", "sent", "sale"])]
        )
        zort_order_ids = [
            order.zort_order_id for order in zort_orders if order.zort_order_id
        ]
        zort_order_ids_str = ",".join(zort_order_ids)
        return zort_order_ids_str

    def _get_marketplace_customer(self, order: dict) -> int:
        """
        Determine the appropriate customer for the Zort order.
        1. For Magento orders, match or create a customer by phone number.
        2. For other platforms, use the marketplace customer.
        :return: res.partner id
        """
        default_customer = self.env.ref("zort_connector.marketplace_customer_1")
        integration_name = (order.get("integrationName") or "").lower()
        customer_phone = order.get("customerphone", "")
        customer_name = order.get("customername", "")
        customer_email = order.get("customeremail", "")

        if integration_name == "magento" and customer_phone:
            customer = self.env["res.partner"].search(
                [("phone", "=", customer_phone)], limit=1
            )
            if customer:
                return customer.id
            if not customer_name:
                return default_customer.id

            try:
                customer = self.env["res.partner"].create(
                    {
                        "name": customer_name,
                        "phone": customer_phone,
                        "email": customer_email,
                        "is_company": False,
                        "customer_type": "person",
                        "customer_platform_code": "magento",
                    }
                )
                return customer.id
            except Exception as e:
                _logger.error("Error creating customer from Magento order: %s", e)
                return default_customer.id

        if integration_name:
            customer = self.env["res.partner"].search(
                [("customer_platform_code", "=", integration_name)], limit=1
            )
            if customer:
                return customer.id

        return default_customer.id

    def action_view_zort_order_json(self):
        """
        Action to view the raw Zort order data in JSON format.
        :return: dict - Action dictionary to open a new window with JSON data.
        """
        return {
            "type": "ir.actions.act_url",
            "url": f"/zort_connector/view_zort_order_json/{self.id}",
            "target": "new",
        }
