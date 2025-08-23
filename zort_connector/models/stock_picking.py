import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "zort.api"]

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

    def button_validate(self):
        res = super().button_validate()
        # Only update qty to zort if the picking is not related to a Zort order
        if not self.sale_id or not getattr(self.sale_id, "is_zort_order", False):
            # TODO: Handle API errors gracefully.
            #       Since button_validate is called after the stock move is done,
            #       it is safe to sync qty to Zort here.
            self._sync_qty_to_zort()
        return res

    def action_sync_qty_to_zort(self):
        """Public action method for server actions."""
        return self._sync_qty_to_zort()

    def _sync_qty_to_zort(self):
        """
        Syncs the quantity of products in Zort based on the stock picking type.
        Uses picking_type_code to decide whether to increase or decrease stock.
        """
        for picking in self:
            data = {"stocks": []}
            # Use move_ids_without_package for outgoing, move_ids for incoming
            moves = (
                picking.move_ids
                if picking.picking_type_code == "incoming"
                else picking.move_ids_without_package
            )
            for move in moves:
                if move.product_id.is_created_on_zort:
                    data["stocks"].append(
                        {
                            "sku": move.product_id.default_code,
                            "stock": move.quantity,
                        }
                    )

            if not data.get("stocks"):
                continue
            if picking.picking_type_code == "incoming":
                wh_code = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("zort_connector.warehouse_code", default="W0001")
                )
                response = self._increase_product_stock_list(
                    warehousecode=wh_code, data=data
                )
                action = _("increased")
            elif picking.picking_type_code == "outgoing":
                response = self._decrease_product_stock_list(
                    warehousecode=wh_code, data=data
                )
                action = _("decreased")
            else:
                continue  # Do nothing for other picking types

            if response.get("error"):
                _logger.error(
                    "Error {} product stock in Zort: {}".format(
                        action, response.get("error")
                    )
                )
                picking.message_post(
                    body=_(
                        "Failed to {action} product stock on Zort: {error}".format(
                            action=action, error=response.get("error")
                        )
                    ),
                    subtype_xmlid="mail.mt_note",
                )
            else:
                self.updated_qty_to_zort = True
                picking.message_post(
                    body=_(f"Product stock {action} successfully on Zort."),
                    subtype_xmlid="mail.mt_note",
                )

    @api.model
    def action_create_return_picking(self):
        """
        Handle Zort return orders by fetching them and creating corresponding
        return pickings in Odoo.

        Logic:
            - Fetch return orders using `_get_zort_return_order()`.
            - For each return order:
            - If status is 'Pending': create assigned return picking.
            - If status is 'Success': done return picking.
        """
        return_orders = self._get_zort_return_order()
        _logger.info("Fetched %d return orders from Zort.", len(return_orders))
        if not return_orders:
            _logger.info("No return orders found in Zort.")
            return

        ########################################
        # Example structure of zort_order_numbers:
        # {
        #     "ZORT-12345": {
        #         "number": "CN-12345",          # Return order number in Zort
        #         "status": "Pending",           # Return status: "Pending" or "Success"
        #         "item_list": [                 # List of returned items
        #             {
        #                 "sku": "SKU-001",      # Product SKU
        #                 "number": 2,           # Quantity returned
        #                 "pricepernumber": 100  # Unit price per item
        #             },
        #             {
        #                 "sku": "SKU-002",
        #                 "number": 1,
        #                 "pricepernumber": 200
        #             }
        #         ]
        #     }
        # }
        ########################################
        zort_order_numbers: dict = {}

        for order in return_orders:
            # On Zort, the sale order number is stored in "referencenumber"
            zort_so_no = order.get("referencenumber")
            status = order.get("status")
            if status in ["Pending", "Success"]:
                zort_order_numbers[zort_so_no] = order

        sale_orders = self.env["sale.order"].search(
            [
                ("zort_order_number", "in", list(zort_order_numbers.keys())),
                ("state", "=", "sale"),
            ]
        )
        for order in sale_orders:
            zort_so_no = order.zort_order_number
            return_order_data = zort_order_numbers.get(zort_so_no, {})
            return_status = return_order_data["status"].lower()

            if return_status == "pending":
                picking_ids = order.picking_ids.filtered(
                    lambda p, order=order: p.state == "done"
                    and p.picking_type_code == "outgoing"
                    and p.origin == order.name
                )
                picking = picking_ids[0] if picking_ids else None
                zort_return_no = return_order_data.get("number", "")
                if picking and not self._created_zort_return_picking(
                    order, zort_return_no
                ):
                    try:
                        # Prepare context for the return wizard
                        return_wizard = (
                            self.env["stock.return.picking"]
                            .with_context(
                                active_ids=[picking.id],
                                active_id=picking.id,
                                active_model="stock.picking",
                            )
                            .create({})
                        )

                        # Prepare item lines for the return wizard
                        # Sample structure:
                        # item_lines = {
                        #     "SKU-001": 2,
                        #     "SKU-002": 1
                        # }
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
                            msg = _(
                                "Zort has created a return order: %(zort_return_no)s",
                                zort_return_no=zort_return_no,
                            )
                            return_picking.message_post(body=msg)
                    except Exception as e:
                        _logger.error(
                            "Error creating return picking for order %s: %s",
                            order.name,
                            str(e),
                        )
                        continue

            elif return_status == "success":
                zort_return_no = return_order_data.get("number", "")
                picking_ids = order.picking_ids.filtered(
                    lambda p, return_no=zort_return_no: p.state == "assigned"
                    and p.picking_type_code == "incoming"
                    and p.zort_return_no == return_no
                )
                if len(picking_ids) > 1:
                    _logger.warning(
                        "Multiple incoming pickings found. Skipping return validation."
                    )
                    continue
                picking = picking_ids[0] if picking_ids else None
                if picking and picking.state == "assigned":
                    picking.button_validate()
                    self._create_credit_note_for_return(picking.ids)
                    _logger.info(
                        "Return picking has been validated for order %s", order.name
                    )

    @api.model
    def _created_zort_return_picking(self, sale_order, zort_return_no) -> bool:
        """
        Returns True if no assigned incoming return picking exists for the sale order.
        """
        incoming_pickings = sale_order.picking_ids.filtered(
            lambda p, return_no=zort_return_no: p.picking_type_code == "incoming"
            and p.state == "assigned"
            and p.zort_return_no == return_no
        )
        _logger.info(
            "Checking existing return pickings for order %s with Zort's return no %s: "
            "found %d",
            sale_order.name,
            zort_return_no,
            len(incoming_pickings),
        )
        return bool(incoming_pickings)

    def _create_credit_note_for_return(self, picking_ids):
        """
        Create a credit note for the return picking.
        This method should be called after the return picking is created.

        Ensure this credit note should be able to reconcile with invoices
        related to the original sale order.
        """

        def get_price_unit(default_code, return_item_list):
            # If return_item_list is available, match SKU to get pricepernumber
            if return_item_list:
                sku_to_price = {
                    item["sku"]: item["pricepernumber"] for item in return_item_list
                }
                return sku_to_price.get(default_code, 0)
            return 0

        for picking in self.env["stock.picking"].browse(picking_ids):
            if (
                picking.picking_type_code != "incoming"
                or not picking.zort_return_no
                or picking.state != "done"
            ):
                continue
            sale_order = picking.sale_id
            if not sale_order:
                continue

            return_item_list = picking.zort_return_data.get("list", [])

            # Prepare lines for credit note: only products in the return picking
            credit_lines = []
            for move in picking.move_ids:
                if move.product_id and move.quantity > 0:
                    credit_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": move.product_id.id,
                                "quantity": move.quantity,
                                "price_unit": get_price_unit(
                                    move.product_id.default_code, return_item_list
                                ),
                            },
                        )
                    )
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
                body=_(
                    "Draft credit note created for return picking: %s", credit_note.name
                )
            )

    @api.model
    def _get_zort_return_order(self, **kwargs) -> list:
        """
        Fetches return orders from Zort
        """
        # TODO: date to query should be configurable on settings

        # Use a default date range of 30 days for get return orders
        returnorderdateafter = (datetime.now() - timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )
        returnorderdatebefore = datetime.now().strftime("%Y-%m-%d")
        kwargs.update(
            {
                "returnorderdateafter": returnorderdateafter,
                "returnorderdatebefore": returnorderdatebefore,
            }
        )

        _logger.info("Fetching return orders from Zort...")
        response = self._get_return_orders(**kwargs)

        # Handle API Read timed out.
        if response.get("error"):
            _logger.error(
                "Error fetching return orders from Zort: %s", response.get("error")
            )
            return []

        res = response.get("res")
        if res.get("resCode") != "200":
            _logger.error(
                "Error fetching return orders from Zort: %s", res.get("resMessage")
            )
            return []

        return response.get("list", [])

    def action_view_return_order_json(self):
        """
        Action to view return order JSON data.
        This method is used to display the return order data in a dialog.
        """
        return {
            "type": "ir.actions.act_url",
            "url": f"/zort_connector/view_zort_return_order_json/{self.id}",
            "target": "new",
        }
