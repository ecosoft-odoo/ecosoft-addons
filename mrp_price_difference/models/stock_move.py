# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _cal_raw_material_cost(self, production):
        total = sum(
            move.product_uom_qty * move.price_unit for move in production.move_raw_ids
        )
        return total

    def _generate_valuation_lines_data(
        self,
        partner_id,
        qty,
        debit_value,
        credit_value,
        debit_account_id,
        credit_account_id,
        description,
    ):
        self.ensure_one()
        # Change credit value to raw material cost
        if self.production_id:
            credit_value = self._cal_raw_material_cost(self.production_id)
        return super()._generate_valuation_lines_data(
            partner_id,
            qty,
            debit_value,
            credit_value,
            debit_account_id,
            credit_account_id,
            description,
        )
