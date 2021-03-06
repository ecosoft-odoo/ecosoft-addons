# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("operating_unit_id")
    def check_operating_unit_id(self):
        for line in self.mapped("invoice_line_ids"):
            if (
                line.analytic_account_id
                and line.operating_unit_id
                and line.operating_unit_id
                not in line.analytic_account_id.operating_unit_ids
            ):
                raise UserError(
                    _(
                        "Configuration error. The Operating Unit in "
                        "the Analytic Account Line must be the same."
                    )
                )

    def copy(self, default=None):
        for rec in self:
            if rec.line_ids.mapped("purchase_order_id"):
                raise UserError(
                    _(
                        "You are not allowed to copy "
                        "an accounting entry to an purchase."
                    )
                )
        return super().copy(default)
