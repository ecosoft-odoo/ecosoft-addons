# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    sale_count = fields.Integer(
        compute="_compute_sale",
        string="Sale Order Count",
        copy=False,
        default=0,
        store=True,
    )
    sale_ids = fields.Many2many(
        comodel_name="sale.order",
        compute="_compute_sale",
        string="Sale Orders",
        copy=False,
        store=True,
    )

    @api.depends("line_ids.sale_line_ids")
    def _compute_sale(self):
        for move in self:
            orders = move.mapped("line_ids.sale_line_ids.order_id")
            move.sale_ids = orders
            move.sale_count = len(orders)

    def action_view_sale_ids(self, orders=False):
        if not orders:
            # sale_ids may be filtered depending on the user.
            # To ensure we get all orders related to the account move,
            # we read them in sudo to fill the cache.
            self.sudo()._read(["sale_ids"])
            orders = self.sale_ids

        result = self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")
        # choose the view_mode accordingly
        if len(orders) > 1:
            result["domain"] = [("id", "in", orders.ids)]
        elif len(orders) == 1:
            res = self.env.ref("sale.view_order_form", False)
            form_view = [(res and res.id or False, "form")]
            if "views" in result:
                result["views"] = form_view + [
                    (state, view) for state, view in result["views"] if view != "form"
                ]
            else:
                result["views"] = form_view
            result["res_id"] = orders.id
        else:
            result = {"type": "ir.actions.act_window_close"}

        return result
