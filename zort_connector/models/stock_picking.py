# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from datetime import timedelta

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)

ZORT_SYNC_STOCK = "zort_sync_stock_picking"
ZORT_GET_RETURN_ORDER = "zort_get_return_order"


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "common.base.api"]

    updated_qty_to_zort = fields.Boolean(
        default=False, help="Indicates if the quantity has been updated to Zort."
    )
    zort_return_data = fields.Json(
        help="Zort return order data",
        copy=False,
    )
    zort_return_no = fields.Char(
        help="Zort return order number",
        copy=False,
    )

    def _get_type_code_skip(self):
        return ["internal"]

    def button_validate(self):
        res = super().button_validate()
        # Only update qty to zort if the picking is not related to a Zort order
        # if not internal transfer update qty to zort
        # Skip internal transfers and MRP operations
        type_code_skip = self._get_type_code_skip()
        if self.picking_type_code in type_code_skip:
            return res

        # Skip if this picking is related to a Zort order
        if self.sale_id and self.sale_id.zort_order_number:
            return res

        # Update quantity to Zort for other picking types
        self.action_sync_qty_to_zort()
        return res

    def action_sync_qty_to_zort(self):
        """Sync available qty to Zort for all products in this picking.

        Delegates API call and response handling to common.base.api via
        action_call_api / _hook_update_data.  Skips pickings that have no
        products linked to Zort.
        """
        for picking in self:
            moves = (
                picking.move_ids
                if picking.picking_type_code == "incoming"
                else picking.move_ids_without_package
            )
            if not any(move.product_id.zort_product_ids for move in moves):
                continue
            picking.action_call_api(ZORT_SYNC_STOCK)

    def _hook_update_data(self, code_api, result):
        """Handle Zort API responses for stock sync and return order fetch."""
        if code_api == ZORT_SYNC_STOCK:
            if result.get("error"):
                _logger.error(
                    "Error syncing stock to Zort for picking %s: %s",
                    self.name,
                    result.get("error"),
                )
            else:
                self.updated_qty_to_zort = True
                _logger.info(
                    "Successfully synced stock to Zort for picking %s", self.name
                )
        elif code_api == ZORT_GET_RETURN_ORDER:
            if result.get("error"):
                _logger.error(
                    "Error fetching return orders from Zort: %s", result.get("error")
                )
                return
            return_orders = result.get("list", [])
            _logger.info("Fetched %d return orders from Zort.", len(return_orders))
            if return_orders:
                self._process_zort_return_orders(return_orders)

    # ==========
    # Return
    # ==========

    @api.model
    def action_create_return_picking(self):
        """Cron entry point: fetch Zort return orders and process them.

        Computes the date window in Python (where timedelta is available) and
        passes it via context so params_code in api.config stays simple.
        Result is dispatched to _hook_update_data → _process_zort_return_orders.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        days_back = int(ICP.get_param("zort_connector.return_order_sync_days_back", 10))
        date_after = (fields.Date.today() - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )
        return self.with_context(zort_return_date_after=date_after).action_call_api(
            ZORT_GET_RETURN_ORDER
        )

    @api.model
    def _process_zort_return_orders(self, return_orders):
        """Process return orders fetched from Zort.

        - Pending: create an assigned return picking from the original delivery.
        - Success: validate the existing return picking and create a credit note.

        Zort return order structure (relevant fields):
            referencenumber  — original sale order number in Zort
            number           — return order number in Zort (CN-xxxxx)
            status           — "Pending" or "Success"
            list             — returned line items [{sku, number, pricepernumber}]
        """
        zort_order_numbers = {
            order["referencenumber"]: order
            for order in return_orders
            if order.get("status") in ("Pending", "Success")
            and order.get("referencenumber")
        }
        if not zort_order_numbers:
            return

        sale_orders = self.env["sale.order"].search(
            [
                ("zort_order_number", "in", list(zort_order_numbers.keys())),
                ("state", "=", "sale"),
            ]
        )
        for order in sale_orders:
            return_order_data = zort_order_numbers[order.zort_order_number]
            zort_return_no = return_order_data.get("number", "")
            return_status = return_order_data["status"].lower()

            if return_status == "pending":
                if self._has_zort_return_picking(order, zort_return_no):
                    continue
                picking = order.picking_ids.filtered(
                    lambda p, so=order: p.state == "done"
                    and p.picking_type_code == "outgoing"
                    and p.origin == so.name
                )[:1]
                if not picking:
                    continue

                try:
                    return_wizard = (
                        self.env["stock.return.picking"]
                        .with_context(
                            active_ids=[picking.id],
                            active_id=picking.id,
                            active_model="stock.picking",
                        )
                        .create({})
                    )
                    item_lines = {
                        item["sku"]: item["number"]
                        for item in return_order_data.get("list", [])
                    }
                    for line in return_wizard.product_return_moves:
                        sku = line.product_id.default_code
                        if sku in item_lines:
                            line.quantity = item_lines[sku]
                    result = return_wizard.action_create_returns()
                    if result and result.get("res_id"):
                        return_picking = self.env["stock.picking"].browse(
                            result["res_id"]
                        )
                        return_picking.write(
                            {
                                "zort_return_no": zort_return_no,
                                "zort_return_data": return_order_data,
                            }
                        )
                        return_picking.message_post(
                            body=self.env._(
                                "Zort has created a return order: %(zort_return_no)s",
                                zort_return_no=zort_return_no,
                            )
                        )
                except Exception as e:
                    _logger.error(
                        "Error creating return picking for order %s: %s",
                        order.name,
                        str(e),
                    )

            elif return_status == "success":
                picking_ids = order.picking_ids.filtered(
                    lambda p, rn=zort_return_no: p.state == "assigned"
                    and p.picking_type_code == "incoming"
                    and p.zort_return_no == rn
                )
                if len(picking_ids) > 1:
                    _logger.warning(
                        "Multiple incoming pickings found for order %s. "
                        "Skipping return validation.",
                        order.name,
                    )
                    continue

                picking = picking_ids[:1]
                if picking:
                    picking.button_validate()
                    picking._create_credit_note_for_return()
                    _logger.info("Return picking validated for order %s", order.name)

    @api.model
    def _has_zort_return_picking(self, sale_order, zort_return_no) -> bool:
        """Return True if an assigned incoming return picking already exists."""
        incoming = sale_order.picking_ids.filtered(
            lambda p, rn=zort_return_no: p.picking_type_code == "incoming"
            and p.state == "assigned"
            and p.zort_return_no == rn
        )
        _logger.info(
            "Checking existing return pickings for order %s with Zort's return no %s: "
            "found %d",
            sale_order.name,
            zort_return_no,
            len(incoming),
        )
        return bool(incoming)

    def _create_credit_note_for_return(self):
        """Create a draft credit note for each done return picking on this recordset.

        The credit note is linked to the original sale order so it can reconcile
        with the existing invoice.
        """
        sku_price_map_cache = {}

        def get_price_unit(default_code, return_item_list):
            if return_item_list:
                if id(return_item_list) not in sku_price_map_cache:
                    sku_price_map_cache[id(return_item_list)] = {
                        item["sku"]: item["pricepernumber"] for item in return_item_list
                    }
                return sku_price_map_cache[id(return_item_list)].get(default_code, 0)
            return 0

        for picking in self:
            if (
                picking.picking_type_code != "incoming"
                or not picking.zort_return_no
                or picking.state != "done"
            ):
                continue
            sale_order = picking.sale_id
            if not sale_order:
                continue

            return_item_list = (picking.zort_return_data or {}).get("list", [])
            credit_lines = [
                Command.create(
                    {
                        "product_id": move.product_id.id,
                        "quantity": move.quantity,
                        "price_unit": get_price_unit(
                            move.product_id.default_code, return_item_list
                        ),
                    }
                )
                for move in picking.move_ids
                if move.product_id and move.quantity > 0
            ]
            if not credit_lines:
                continue

            credit_note = self.env["account.move"].create(
                {
                    "move_type": "out_refund",
                    "invoice_origin": sale_order.name,
                    "invoice_user_id": sale_order.user_id.id,
                    "partner_id": sale_order.partner_id.id,
                    "invoice_date": fields.Date.context_today(self),
                    "invoice_line_ids": credit_lines,
                    "invoice_payment_term_id": sale_order.payment_term_id.id,
                    "ref": f"Picking No. {picking.name}",
                }
            )
            picking.message_post(
                body=self.env._(
                    "Draft credit note created for return picking: %s",
                    credit_note.name,
                )
            )
