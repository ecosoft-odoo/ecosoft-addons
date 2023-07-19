# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _cal_work_center_cost(self, production):
        work_center_cost = 0.0
        for work_order in production.workorder_ids:
            duration = sum(work_order.time_ids.mapped("duration"))
            work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
        return work_center_cost

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
        # Change debit and credit value
        if self.production_id:
            raw_material_cost = self._cal_raw_material_cost(self.production_id)
            work_center_cost = self._cal_work_center_cost(self.production_id)
            debit_value = raw_material_cost + work_center_cost
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
