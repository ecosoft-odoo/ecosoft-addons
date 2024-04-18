# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import FORMATS


class ReportStockLocationXlsx(models.TransientModel):
    _inherit = "report.stock_report_xlsx.report_stock_location_xlsx"

    def _get_stock_location_template(self):
        stock_location_template = super()._get_stock_location_template()

        stock_location_template["6_cost"] = {
            "header": {"value": "Cost"},
            "data": {
                "value": self._render("cost"),
                "format": FORMATS["format_tcell_amount_right"],
            },
            "width": 20,
        }
        stock_location_template["7_avg_cost_unit"] = {
            "header": {"value": "Average Cost / Unit"},
            "data": {
                "value": self._render("avg_cost_unit"),
                "format": FORMATS["format_tcell_amount_right"],
            },
            "width": 20,
        }
        stock_location_template["8_sale_price"] = {
            "header": {"value": "Sale Price"},
            "data": {
                "value": self._render("sale_price"),
                "format": FORMATS["format_tcell_amount_right"],
            },
            "width": 20,
        }
        stock_location_template["9_sale_price_unit"] = {
            "header": {"value": "Sale Price / Unit"},
            "data": {
                "value": self._render("sale_price_unit"),
                "format": FORMATS["format_tcell_amount_right"],
            },
            "width": 20,
        }
        return stock_location_template

    def _get_render_space(self, index, line):
        render_space = super()._get_render_space(index, line)

        # Add cost in report
        product_company = line.product_id.with_company(line.company_id)
        value = 0.0
        if product_company.quantity_svl:
            value = (
                line.quantity * product_company.value_svl / product_company.quantity_svl
            )
        render_space["cost"] = value
        render_space["avg_cost_unit"] = line.quantity and (value / line.quantity) or 0.0
        render_space["sale_price_unit"] = product_company.list_price
        render_space["sale_price"] = product_company.list_price * line.quantity
        return render_space
