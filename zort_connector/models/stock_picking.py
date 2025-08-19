import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "zort.api"]

    def button_validate(self):
        res = super().button_validate()
        # Only update qty to zort if the picking is not related to a Zort order
        if not self.sale_id or not getattr(self.sale_id, "is_zort_order", False):
            # TODO: Handle API errors gracefully.
            #       Since button_validate is called after the stock move is done,
            #       it is safe to sync qty to Zort here.
            self._sync_qty_to_zort()
        return res

    def _sync_qty_to_zort(self):
        """
        Syncs the quantity of products in Zort based on the stock picking type.
        Uses picking_type_code to decide whether to increase or decrease stock.
        """
        for picking in self:
            data = []
            # Use move_ids_without_package for outgoing, move_ids for incoming
            moves = (
                picking.move_ids
                if picking.picking_type_code == "incoming"
                else picking.move_ids_without_package
            )
            for move in moves:
                if move.product_id.is_created_on_zort:
                    data.append(
                        {
                            "sku": move.product_id.default_code,
                            "qty": move.quantity,
                        }
                    )
            if not data:
                continue
            if picking.picking_type_code == "incoming":
                response = self._increase_product_stock_list(
                    warehousecode="W0001", data=data
                )
                action = _("increased")
            elif picking.picking_type_code == "outgoing":
                response = self._decrease_product_stock_list(
                    warehousecode="W0001", data=data
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
                picking.message_post(
                    body=_(f"Product stock {action} successfully on Zort."),
                    subtype_xmlid="mail.mt_note",
                )
