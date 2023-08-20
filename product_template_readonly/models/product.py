# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def create(self, values):
        if not self.env.user.has_group("base.group_erp_manager"):
            raise UserError(
                _(
                    "You are not allowed to create product, please contact Administration"
                )
            )
        return super().create(values)

    def write(self, vals):
        if not self.env.user.has_group("base.group_erp_manager"):
            raise UserError(
                _("You are not allowed to edit product, please contact Administration")
            )
        return super().write(vals)
