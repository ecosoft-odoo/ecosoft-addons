# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_analytic_tags",
        store=True,
        readonly=False,
        index=True,
    )

    @api.depends("production_id", "raw_material_production_id")
    def _compute_analytic_tags(self):
        for rec in self.sudo():
            rec.analytic_tag_ids = (
                rec.analytic_tag_ids
                or rec.production_id.analytic_tag_ids
                or rec.raw_material_production_id.analytic_tag_ids
                or False
            )

    def _get_new_picking_values(self):
        data_dict = super()._get_new_picking_values()
        mrp = self.env["mrp.production"].browse(self._context.get("mo_ids", []))
        if mrp:
            data_dict["analytic_account_id"] = mrp.analytic_account_id.id
            self.write({"analytic_tag_ids": [(6, 0, mrp.analytic_tag_ids.ids)]})
        return data_dict
