# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains("operating_unit_id")
    def check_operating_unit_id(self):
        for rec in self:
            # find lines is not section and note
            for line in rec.order_line.filtered(lambda l: not l.display_type):
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
            for line in invoice.invoice_line_ids.filtered(
                lambda l: l.account_id.asset_profile_id
            ):
                line.asset_profile_id = line.account_id.asset_profile_id
        return res
