# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains("operating_unit_id")
    def check_operating_unit_id(self):
        for rec in self:
            for line in rec.order_line:
                if (
                    line.operating_unit_id
                    not in line.account_analytic_id.operating_unit_ids
                ):
                    raise UserError(
                        _(
                            "Configuration error. The Operating Unit in"
                            " the Analytic Account Line must be the same."
                        )
                    )

    def action_create_invoice(self):
        res = super().action_create_invoice()
        if res.get("res_model", False) == "account.move" and res.get("res_id", False):
            invoice = self.env["account.move"].browse(res["res_id"])
            # Trigger onchange account
            # eg. onchange asset profile following account
            for line in invoice.invoice_line_ids:
                line._onchange_account_id()
        return res
