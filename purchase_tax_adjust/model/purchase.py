# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _amount_all(self):
        super()._amount_all()
        for order in self:
            adjust_tax = sum(order.order_line.mapped("adjust_tax"))
            if adjust_tax:
                order.update(
                    {
                        "amount_tax": order.amount_tax + adjust_tax,
                        "amount_total": order.amount_total + adjust_tax,
                    }
                )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    adjust_tax = fields.Monetary(
        help="Minor tax adjustment, i.e., +/- 0.01, to recompute total tax amount",
    )
