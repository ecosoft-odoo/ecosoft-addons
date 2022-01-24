# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("operating_unit_id")
    def check_operating_unit_id(self):
        for rec in self:
            for line in rec.invoice_line_ids:
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
