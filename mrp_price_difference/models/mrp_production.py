# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_consumed_moves(self):
        self.ensure_one()
        # Use stock moves of Transfer as consumed_moves instead
        pickings = self.picking_ids
        scraps = self.env["stock.scrap"].search([("picking_id", "in", pickings.ids)])
        consumed_moves = pickings.mapped("move_lines") + scraps.mapped("move_id")
        return consumed_moves

    def _cal_price(self, consumed_moves):
        self.ensure_one()
        if self.location_src_id.usage != "internal":
            consumed_moves = self._get_consumed_moves()
        return super()._cal_price(consumed_moves)
