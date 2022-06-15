# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_exception = fields.Boolean(
        string="Amount INV(s) > PO",
        compute="_compute_amount_exception",
        store=True,
        readonly=True,
        help="Total amount exceed amount of its origin purchase order",
    )
    bypass_amount_exception = fields.Boolean(
        string="Bypass Amount Exception",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    @api.depends("amount_total")
    def _compute_amount_exception(self):
        """Amount in all posted bills, shouldn't exceed its PO amount"""
        for rec in self:
            # PO amount
            purchases = rec.line_ids.mapped("purchase_order_id")
            if not purchases:
                rec.amount_exception = False
                continue
            amount_po = sum(purchases.mapped("amount_total"))
            # Invoice(s) amount
            other_amount = sum(
                purchases.mapped("invoice_ids")
                .filtered(lambda l: l.state == "posted")
                .mapped("amount_total")
            )
            this_amount = rec.amount_total if rec.state == "draft" else 0
            amount_inv_all = other_amount + this_amount
            rec.amount_exception = (
                True if float_compare(amount_inv_all, amount_po, 2) == 1 else False
            )
