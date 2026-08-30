# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import json
import logging

from odoo import Command, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    zort_order_id = fields.Many2one(
        comodel_name="zort.order",
        copy=False,
        readonly=True,
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
    zort_sales_channel = fields.Char(
        help="The sales channel of the order in Zort.",
        copy=False,
        readonly=True,
    )
    zort_customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="e-Commerce Customer",
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

    # -------------------------------------------------------------------------
    # Update flow (called from zort.order._post_upsert_order)
    # -------------------------------------------------------------------------

    def _update_sale_order_from_zort(self, zort_rec):
        """Update this sale order's Zort fields from the linked zort.order record."""
        zort_order = json.loads(zort_rec.raw_data or "{}")
        self.write(
            {
                "zort_order_number": zort_rec.zort_order_number,
                "zort_order_status": zort_rec.zort_status,
                "zort_payment_status": zort_order.get("paymentstatus"),
                "zort_sales_channel": zort_rec.source_channel,
            }
        )
        self.validate_order_from_zort()
        _logger.info("Updated Sale Order: %s", self.name)
        self._handle_zort_order_status(zort_rec.zort_status)

    def _handle_zort_order_status(self, zort_status):
        """Trigger Odoo workflow actions based on Zort order status."""
        if zort_status == "Voided":
            self.with_context(disable_cancel_warning=True).action_cancel()
        elif zort_status == "Success" and self.validate_zort_order:
            self._process_success_order()

    def _process_success_order(self):
        """Confirm, deliver, and invoice this order when Zort status is 'Success'."""
        if self.state not in ["sale", "cancel"]:
            self.action_confirm()
        for picking in self.picking_ids:
            if picking.state not in ["done", "cancel"]:
                picking.button_validate()
        _logger.info("Delivery order done for Sale Order: %s", self.name)
        self.order_line.invalidate_recordset(["qty_delivered"])
        self.order_line._compute_qty_delivered()
        self._create_draft_invoice()

    def _create_draft_invoice(self):
        """Create a draft invoice for this sale order."""
        invoice_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=self.ids, active_id=self.id)
            .create({"advance_payment_method": "delivered"})
        )
        invoice_wizard.create_invoices()
        _logger.info("Draft invoice created for Sale Order: %s", self.name)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def action_validate_zort_order(self):
        """Validate Zort orders that are in draft state and
        have a linked zort.order record"""
        orders = self.env["sale.order"].search(
            [
                ("state", "=", "draft"),
                ("zort_order_id", "!=", False),
                ("validate_zort_order", "=", False),
            ]
        )
        if not orders:
            return
        orders.validate_order_from_zort()
        confirmed = orders.filtered(lambda so: so.validate_zort_order)
        for order in confirmed:
            order.action_confirm()
        _logger.info("Confirmed Sale Order from Zort: %s", confirmed.mapped("name"))

    def validate_order_from_zort(self):
        """
        Validate this sale order against the linked zort.order record.
        Checks:
          1. Total amount matches zort.order.raw_data["amount"].
          2. All Zort product IDs are present in order lines.
        """
        for order in self:
            zort_data = json.loads(order.zort_order_id.raw_data or "{}")
            zort_amount = zort_data.get("amount", 0.0)
            msgs = []

            if float(zort_amount) != float(order.amount_total):
                msgs.append(
                    f"Amount mismatch: Zort amount is {zort_amount}, "
                    f"Odoo amount is {order.amount_total}."
                )

            existing_zort_ids = set(
                order.order_line.mapped("product_id.zort_product_ids.id_zort_product")
            )
            zort_product_count = 0
            missing_product_ids = []
            for line in zort_data.get("list", []):
                if line.get("id"):
                    zort_product_count += 1
                pid = line.get("productid")
                if pid and pid not in existing_zort_ids:
                    missing_product_ids.append(str(pid))

            odoo_product_count = len(
                order.order_line.filtered(lambda ln: ln.product_id.type != "service")
            )
            if zort_product_count != odoo_product_count:
                msgs.append(
                    f"Line item count mismatch: Zort has {zort_product_count} items, "
                    f"Odoo has {odoo_product_count} items."
                )

            validated = not msgs
            order.write(
                {
                    "zort_missing_product_ids": ",".join(missing_product_ids),
                    "validate_zort_order": validated,
                    "zort_validation_message": (
                        "This order has been validated successfully."
                        if validated
                        else "\n".join(msgs)
                    ),
                }
            )

    def update_zort_sale_order_line(self):
        """Add missing product lines from the linked zort.order's raw_data."""
        for order in self:
            zort_data = json.loads(order.zort_order_id.raw_data or "{}")
            zort_line_items = zort_data.get("list", [])
            existing_zort_ids = set(
                order.order_line.mapped("product_id.zort_product_ids.id_zort_product")
            )
            for zort_line in zort_line_items:
                if zort_line.get("id") in existing_zort_ids:
                    continue

                product = order.zort_order_id._get_product_by_sku(
                    zort_line.get("productid")
                )
                if not product:
                    _logger.warning(
                        "Product with Zort ID %s not found. Skipping line.",
                        zort_line.get("id"),
                    )
                    continue
                order.write(
                    {
                        "order_line": [
                            Command.create(
                                {
                                    "product_id": product.id,
                                    "product_uom_qty": zort_line.get("number", 1),
                                    "price_unit": zort_line.get("pricepernumber", 0.0),
                                    "name": product.name,
                                    "tax_id": [
                                        Command.set(
                                            order.env.company.zort_default_tax_id.ids
                                        )
                                    ],
                                }
                            )
                        ]
                    }
                )
        return True
