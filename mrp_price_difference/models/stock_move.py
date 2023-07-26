# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _cal_raw_material_cost(self, production):
        consumed_moves = production._get_consumed_moves()
        total_rm_cost = -sum(
            consumed_moves.sudo().stock_valuation_layer_ids.mapped("value")
        )
        return total_rm_cost

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
        # Change debit and credit value
        if self.production_id:
            raw_material_cost = self._cal_raw_material_cost(self.production_id)
            credit_value = raw_material_cost
        return super()._generate_valuation_lines_data(
            partner_id,
            qty,
            debit_value,
            credit_value,
            debit_account_id,
            credit_account_id,
            description,
        )
