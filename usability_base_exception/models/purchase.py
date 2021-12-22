# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
from odoo import api, fields, models
from odoo.tools.float_utils import float_compare

from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    amount_exception = fields.Boolean(
        string="Amount PO > PR",
        compute="_compute_amount_exception",
        store=True,
        readonly=True,
        help="Total amount exceed amount of its origin purchase request",
    )
    bypass_amount_exception = fields.Boolean(
        string="Bypass Amount Exception",
        states=Purchase.READONLY_STATES,
        tracking=True,
    )

    @api.depends("amount_total")
    def _compute_amount_exception(self):
        """ Amont in PO, shouldn't exceed its PR amount """
        for rec in self:
            request_lines = rec.order_line.mapped("purchase_request_lines")
            if not request_lines:
                rec.amount_exception = False
                continue
            amount_pr = sum(request_lines.mapped("estimated_cost"))
            rec.amount_exception = (
                True if float_compare(rec.amount_total, amount_pr, 2) == 1 else False
            )
