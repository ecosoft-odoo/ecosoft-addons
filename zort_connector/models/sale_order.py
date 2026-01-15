# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import logging
import time
from datetime import datetime, timedelta

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
    zort_sales_channel = fields.Char(
        help="The sales channel of the order in Zort.",
        copy=False,
        readonly=True,
    )
    zort_customer_id = fields.Many2one(
        "res.partner",
        "e-Commerce Customer",
        copy=False,
        readonly=True,
    )
    validate_zort_order = fields.Boolean(
        help="Indicates if the Zort order has been validated.",
        copy=False,
        default=False,
        readonly=True,
    )
    zort_missing_product_ids = fields.Char(
        help="Comma-separated list of Zort product IDs that are missing in Odoo.",
        copy=False,
        readonly=True,
    )
    zort_validation_message = fields.Text(
        help="Validation warning messages from Zort order synchronization.",
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
        if not zort_ids:
            return

        page = 1
        limit = 500
        max_pages = 500  # Safety limit to prevent infinite loops
        while page <= max_pages:
            res = self._get_list_order(
                status="", orderidlist=zort_ids, page=page, limit=limit
            )
            # TODO: Handle API errors properly
            # on this point, we just break the loop
            if res.get("error"):
                _logger.error(
                    "Error fetching orders from Zort: %s",
                    res.get("error"),
                )
                break
            orders = res.get("list", [])
            if not orders:
                break

            for order in orders:
                try:
                    so = self.search([("zort_order_id", "=", order.get("id"))], limit=1)
                    if so:
                        self._update_sale_order_from_zort(so, order)
                except Exception as e:
                    _logger.error("Error updating existing sale order from Zort: %s", e)
            page += 1
            time.sleep(5)

    def _update_sale_order_from_zort(self, sale_order, zort_order):
        """Update a single sale order with Zort data and handle status changes."""
        # Update order data
        sale_order.write(
            {
                "zort_order_number": zort_order.get("number"),
                "zort_order_status": zort_order.get("status"),
                "zort_payment_status": zort_order.get("paymentstatus"),
                "zort_sales_channel": zort_order.get("saleschannel"),
                "zort_order_data": zort_order,
            }
        )
        sale_order.validate_order_from_zort()
        _logger.info("Updated Sale Order: %s", sale_order.name)

        # Handle status-based actions
        self._handle_zort_order_status(sale_order, zort_order.get("status"))

    def _handle_zort_order_status(self, sale_order, zort_status):
        """Handle order workflow based on Zort order status."""
        if zort_status == "Voided":
            sale_order.with_context(disable_cancel_warning=True).action_cancel()
        elif zort_status == "Success":
            if sale_order.validate_zort_order:
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
        """Create new sale orders from Zort data with exponential backoff."""
        _logger.info("Creating Sale Order from Zort...")

        zort_ids = [
            int(id)
            for id in self._get_existing_zort_order_ids().split(",")
            if id.strip()
        ]

        page = 1
        limit = 500
        orderdateafter = self.get_order_date_after()
        max_pages = 500  # Safety limit to prevent infinite loops
        while page <= max_pages:
            res = self._get_list_order(
                status=status,
                orderidlist=orderidlist,
                numberlist=numberlist,
                page=page,
                limit=limit,
                orderdateafter=orderdateafter,
            )
            # TODO: Handle API errors properly
            # on this point, we just break the loop
            if res.get("error"):
                _logger.error(
                    "Error fetching orders from Zort: %s",
                    res.get("error"),
                )
                break

            orders = res.get("list", [])
            if not orders:
                break

            for order in orders:
                try:
                    if order.get("id") in zort_ids:
                        continue
                    self._create_single_sale_order(order)
                    _logger.info(
                        "Successfully created Sale Order from Zort order %s",
                        order.get("id"),
                    )
                except Exception as e:
                    _logger.error(
                        "Error creating sale order from Zort order %s: %s",
                        order.get("id"),
                        e,
                    )
            page += 1
            time.sleep(5)

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
            "zort_sales_channel": zort_order.get("saleschannel"),
            "zort_order_data": zort_order,
            "zort_customer_id": self._get_platform_customer(zort_order),
        }

        # Create the sale order
        sale_order = self.create(order_data)

        # Add order lines
        order_lines = self._prepare_order_lines(zort_order)
        if order_lines:
            sale_order.order_line = order_lines

        # validate sale order first
        sale_order.validate_order_from_zort()
        if sale_order.validate_zort_order:
            sale_order.action_confirm()
        _logger.info("Created Sale Order: %s", sale_order.name)

    @staticmethod
    def hook_process_sku(sku):
        """
        Hook to process SKU before fetching product.
        Override in custom modules to modify SKU format if needed.
        Example: Remove suffix after '#' (e.g., 'a-1234#left' -> 'a-1234').
        """
        return sku

    def get_product_by_sku(self, sku):
        """
        Fetch product by SKU (default_code).
        """
        id = self.hook_process_sku(sku)
        zort_product = self.env["zort.product"].search(
            [("id_zort_product", "=", id)], limit=1
        )
        if zort_product and zort_product.product_id:
            return zort_product.product_id
        return self.env["product.product"]

    def _prepare_order_lines(self, zort_order):
        """
        Prepare order lines from Zort order data."""
        order_lines = []
        # Add product lines
        for line in zort_order.get("list", []):
            # Instead of send sku, send zort product id.
            product = self.get_product_by_sku(line.get("productid"))
            if not product:
                _logger.warning(
                    "Product with SKU %s not found. Skipping line.",
                    line.get("sku"),
                )
                continue

            company = self.env.company
            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": line.get("number", 1),
                        "price_unit": line.get("pricepernumber", 0.0),
                        "name": product.name,
                        "tax_id": [(6, 0, company.zort_default_tax_id.ids)],
                    },
                )
            )

        # Add shipping fee if exists
        shipping_amount = zort_order.get("shippingamount", 0.0)
        if shipping_amount > 0:
            order_lines.append(self._add_shipping_fee_line(shipping_amount))

        # Add discount if exists
        discount = zort_order.get("discount", 0.0)
        if discount and isinstance(discount, str):
            discount = float(discount)
            order_lines.append(self._add_discount_line(discount))

        # Add voucher_amount if exists
        voucher_amount = zort_order.get("voucheramount", 0.0)
        if voucher_amount > 0:
            order_lines.append(self._add_voucher_line(voucher_amount))

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

    def _add_discount_line(self, discount):
        """Add a discount line to the sale order."""
        discount_product = self.env["product.product"].search(
            [("default_code", "=", "zort_discount")], limit=1
        )
        if isinstance(discount, str):
            discount = float(discount)

        return (
            0,
            0,
            {
                "product_id": discount_product.id,
                "product_uom_qty": 1,
                "price_unit": -discount,
                "name": "Discount",
            },
        )

    def _add_voucher_line(self, voucher_amount):
        """Add a voucher line to the sale order."""
        voucher_product = self.env["product.product"].search(
            [("default_code", "=", "zort_voucher")], limit=1
        )
        return (
            0,
            0,
            {
                "product_id": voucher_product.id,
                "product_uom_qty": 1,
                "price_unit": voucher_amount,
                "name": "Voucher",
            },
        )

    def _get_existing_zort_order_ids(self):
        """
        Get existing Zort orders (id) in draft, sent, or sale state
        Return as comma-separated string Ex. "1234,5678,91011"
        """
        days_back = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.order_sync_days_back", default="10")
        )
        try:
            days = int(days_back)
            if days <= 0:
                days = 10
        except (TypeError, ValueError):
            days = 10
        orderdateafter = datetime.now() - timedelta(days=days)
        zort_orders = self.search(
            [
                ("is_zort_order", "=", True),
                ("state", "in", ["draft", "sent", "sale"]),
                ("date_order", ">=", orderdateafter),
            ]
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
        sales_channel = (order.get("saleschannel") or "").lower()

        # check if ecommerce channel use platform customer
        ecommerce_channel = self.env["zort.ecommerce.channel"].search(
            [("code", "=", sales_channel)], limit=1
        )
        platform_customer_id = (
            ecommerce_channel.partner_id.id
            if ecommerce_channel and ecommerce_channel.partner_id
            else default_customer.id
        )
        return platform_customer_id

    def _get_platform_customer(self, order: dict) -> int:
        """
        Get the platform customer (res.partner) for the Zort order.
        :return: res.partner id
        """
        sales_channel = (order.get("saleschannel") or "").lower()

        ecommerce_channel = self.env["zort.ecommerce.channel"].search(
            [("code", "=", sales_channel)], limit=1
        )
        if ecommerce_channel and ecommerce_channel.auto_create_customer:
            customer = self.create_new_customer(order)
            if customer:
                return customer.id

        return False

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

    @api.model
    def create_new_customer(self, order_data: dict):
        """
        Create a new customer based on the provided keyword arguments.
        Make sure each key in kwargs matches a field in res.partner model.
        Example kwargs: {
            'name': 'John Doe',
            'phone': '1234567890',
            'email': 'john.doe@example.com'
        }
        :return: res.partner record
        """
        vals = {
            "name": order_data.get("customername", "Online Customer"),
            "phone": order_data.get("customerphone", ""),
            "email": order_data.get("customeremail", ""),
            "street": order_data.get("customeraddress", ""),
            "city": order_data.get("customerprovince", ""),
            "zip": order_data.get("customerpostcode", ""),
            "vat": order_data.get("customeridnumber", ""),
            "is_company": False,
        }
        existing_customer = None
        if vals["phone"]:
            phone = self.validate_customer_phone(vals["phone"])
            existing_customer = self.env["res.partner"].search(
                [("phone", "=", phone)], limit=1
            )
        if vals["vat"]:
            existing_customer = self.env["res.partner"].search(
                [("vat", "=", vals["vat"])], limit=1
            )
        if existing_customer:
            return existing_customer

        new_customer = self.env["res.partner"].create(vals)
        return new_customer

    @staticmethod
    def validate_customer_phone(phone: str) -> str:
        """
        Return the last 9 digits of the phone number.
        :param phone: str - Phone number to process.
        :return: str - Last 9 digits of the phone number.
        """
        phone = phone.strip()
        return phone[-9:] if len(phone) >= 9 else phone

    def get_order_date_after(self):
        """
        Get the order date after value from configuration.
        :return: str - Date in 'YYYY-MM-DD' format.
        """
        days_back = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.order_sync_days_back", default="10")
        )
        try:
            days = int(days_back)
            if days <= 0:
                days = 10
        except (TypeError, ValueError):
            days = 10

        orderdateafter = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return orderdateafter

    def validate_order_from_zort(self):
        """
        Validate the order data received from Zort.
        1. By check zort_order_data.get("amount") compare with sale order amount_total.
        2. Check line item from zort_order_data.get("list") each zort product id
            compare with product_id.zort_product_ids in sale order lines.

        :return: bool - True if validation passes, False otherwise.
        """
        for order in self:
            zort_data = order.zort_order_data or {}
            zort_amount = zort_data.get("amount", 0.0)
            validated = True
            msg = ""
            if float(zort_amount) != float(order.amount_total):
                msg += (
                    f"Amount mismatch: Zort amount is {zort_amount}, "
                    f"Odoo amount is {order.amount_total}.\n"
                )
                validated = False

            zort_line_items = zort_data.get("list", [])
            zort_product_count = len(
                [line for line in zort_line_items if line.get("id")]
            )
            odoo_product_count = len(
                order.order_line.filtered(
                    lambda line: line.product_id.type != "service"
                )
            )
            if zort_product_count != odoo_product_count:
                # This condition in sale order line not include discount,
                # shipping, voucher lines
                msg += (
                    f"Line item count mismatch: Zort has {zort_product_count} items, "
                    f"Odoo has {odoo_product_count} items.\n"
                )

            missing_product_ids = []
            existing_zort_ids = set(
                order.order_line.mapped("product_id.zort_product_ids.id_zort_product")
            )
            for zort_line in zort_line_items:
                zort_product_id = zort_line.get("productid")
                if zort_product_id not in existing_zort_ids:
                    missing_product_ids.append(str(zort_product_id))

            order.zort_missing_product_ids = ",".join(missing_product_ids)
            order.zort_validation_message = msg.strip()
            order.validate_zort_order = bool(validated)
            if order.validate_zort_order:
                order.zort_validation_message = (
                    "This order has been validated successfully."
                )
        return bool(validated)

    def update_zort_sale_order_line(self):
        """
        Update sale order lines based on the latest Zort order data.
        Just add missing products from order data (Json).
        """
        for order in self:
            zort_data = order.zort_order_data or {}
            zort_line_items = zort_data.get("list", [])
            existing_zort_ids = set(
                order.order_line.mapped("product_id.zort_product_ids.id_zort_product")
            )
            for zort_line in zort_line_items:
                zort_product_id = zort_line.get("id")
                if zort_product_id in existing_zort_ids:
                    continue

                product = self.get_product_by_sku(zort_line.get("productid"))
                if not product:
                    _logger.warning(
                        "Product with Zort ID %s not found. Skipping line.",
                        zort_product_id,
                    )
                    continue

                order.write(
                    {
                        "order_line": [
                            (
                                0,
                                0,
                                {
                                    "product_id": product.id,
                                    "product_uom_qty": zort_line.get("number", 1),
                                    "price_unit": zort_line.get("pricepernumber", 0.0),
                                    "name": product.name,
                                    "tax_id": [
                                        (
                                            6,
                                            0,
                                            order.env.company.zort_default_tax_id.ids,
                                        )
                                    ],
                                },
                            )
                        ]
                    }
                )
        return True
