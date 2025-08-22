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
    )
    zort_order_id = fields.Char(
        help="The ID of the order in Zort.",
        copy=False,
        readonly=True,
    )
    zort_order_number = fields.Char(
        help="The order number in Zort.",
        copy=False,
        readonly=True,
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
    def create_sales_order_from_zort(self, status="0", orderidlist="", numberlist=""):
        """
        Fetch orders from Zort based on the provided status and optional filters.

        :param status: str
            Status of the orders to fetch.
        :param orderidlist: str
            Comma-separated list of order IDs to filter (optional).
        :param numberlist: str
            Comma-separated list of order numbers to filter (optional).
        :return: dict
            JSON response containing the list of orders.
        """

        response = self._get_list_order(status, orderidlist, numberlist)

        if response.get("count") == 0:
            _logger.warning("No orders fetched from Zort for the given criteria.")
            return

        orders = response.get("list", [])
        for order in orders:
            try:
                self._create_or_update_sale_order(order)
            except Exception as e:
                _logger.error("Error creating/updating sale order: %s", e)

    @api.model
    def update_sale_order_status(self):
        """
        Update the status or relate field of a sale order if it is a Zort order.
        Use cron job to periodically check and update the status of Zort orders.
        :return: None
        """
        zort_orders = self.search(
            [("is_zort_order", "=", True), ("state", "in", ["draft", "sent", "sale"])]
        )
        zort_order_ids = [
            order.zort_order_id for order in zort_orders if order.zort_order_id
        ]
        zort_order_ids_str = ",".join(zort_order_ids)

        response = self._get_list_order(status="", orderidlist=zort_order_ids_str)

        orders = response.get("list", [])
        for order in orders:
            try:
                self._create_or_update_sale_order(order)
            except Exception as e:
                _logger.error("Error processing Zort order %s: %s", order.get("id"), e)

    def _create_or_update_sale_order(self, order):
        """
        Create or update a sale order based on the Zort order data.
        :param order: dict - The Zort order data.
        """
        # Check if the order already exists in Odoo
        existing_order = self.search([("zort_order_id", "=", order.get("id"))], limit=1)
        if existing_order:
            # Update existing order
            existing_order.write(
                {
                    "zort_order_number": order.get("number"),
                    "zort_order_status": order.get("status"),
                    "zort_payment_status": order.get("paymentstatus"),
                    "zort_order_data": order,
                }
            )
            _logger.info("Updated Sale Order: %s", existing_order.name)

            # If zort order status is 'voided', cancel the order
            # If zort order status is 'waiting', confirm the order
            # If Zort order status is 'success',
            # mark delivery order as done and create draft invoice
            if existing_order.zort_order_status == "Voided":
                existing_order.action_cancel()
            if existing_order.zort_order_status == "Waiting":
                existing_order.action_confirm()
            if existing_order.zort_order_status == "Success":
                # Maybe zort order skip from 'Pending' to 'Success'
                # so we need to check if there is already confirm.
                if existing_order.state not in ["done", "cancel"]:
                    existing_order.action_confirm()

                for picking in existing_order.picking_ids:
                    if picking.state not in ["done", "cancel"]:
                        picking.button_validate()
                _logger.info(
                    "Delivery order done for Sale Order: %s", existing_order.name
                )

                # Force recomputation of delivered quantities
                existing_order.order_line.invalidate_recordset(["qty_delivered"])
                existing_order.order_line._compute_qty_delivered()

                # Create draft invoice programmatically
                # This following code base on invoice policy.
                invoice_wizard = (
                    self.env["sale.advance.payment.inv"]
                    .with_context(
                        active_ids=existing_order.ids, active_id=existing_order.id
                    )
                    .create(
                        {
                            "advance_payment_method": "delivered",
                        }
                    )
                )
                invoice_wizard.create_invoices()
                _logger.info(
                    "Draft invoice created for Sale Order: %s", existing_order.name
                )
            return

        else:
            # Create a new sale order
            _logger.info("Creating Sale Order for Zort Order ID: %s", order.get("id"))

            # Prepare the data for the sale order
            order_data = {
                "partner_id": self._get_marketplace_customer(order),
                "is_zort_order": True,
                "zort_order_id": order.get("id"),
                "zort_order_number": order.get("number"),
                "zort_order_status": order.get("status"),
                "zort_payment_status": order.get("paymentstatus"),
                "zort_order_data": order,
            }

            # Create the sale order
            sale_order = self.create(order_data)

            # Add order lines
            order_lines = []
            for line in order.get("list", []):
                product = self.env["product.product"].search(
                    [("default_code", "=", line.get("sku"))], limit=1
                )
                if not product:
                    _logger.warning(
                        "Product with SKU %s not found. Skipping line.", line.get("sku")
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

            # check if there is shipping fee
            if order.get("shippingamount", 0.0) > 0:
                shipping_fee_product = self.env["product.product"].search(
                    [("default_code", "=", "shipping_fee")], limit=1
                )
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": shipping_fee_product.id,
                            "product_uom_qty": 1,
                            "price_unit": order.get("shippingamount", 0.0),
                            "name": "Shipping Fee",
                        },
                    )
                )

            # check if there is discount
            if order.get("discountamount", 0.0) > 0:
                discount_product = self.env["product.product"].search(
                    [("default_code", "=", "zort_discount")], limit=1
                )
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": discount_product.id,
                            "product_uom_qty": 1,
                            "price_unit": -order.get("discountamount", 0.0),
                            "name": "Discount",
                        },
                    )
                )

            if order_lines:
                sale_order.order_line = order_lines

            _logger.info("Created Sale Order: %s", sale_order.name)

        return sale_order

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
