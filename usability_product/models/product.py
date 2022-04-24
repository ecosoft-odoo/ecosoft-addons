# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Product(models.Model):
    _inherit = "product.template"

    product_important = fields.Selection(
        selection=[
            ("edit", "Editable"),
            ("not_edit", "Not Editable"),
        ],
        default="edit",
        string="Important",
    )
    is_editable = fields.Boolean(
        compute="_compute_is_editable",
    )

    @api.depends("product_important", "name")
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = self.env.user.has_group("base.group_system")

    def write(self, vals):
        model = self._context.get("active_model", False)
        if (
            model in [False, "product.template"]
            and self.product_important == "not_edit"
            and not self.env.user.has_group("base.group_system")
        ):
            raise UserError(
                _(
                    "{} can not editable. Please contact administrator.".format(
                        self.name
                    )
                )
            )
        return super().write(vals)
