# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import FORMATS


class ReportStockLocationXlsx(models.TransientModel):
    _inherit = "report.stock_report_xlsx.report_stock_location_xlsx"

    def _get_stock_location_template(self):
        stock_location_template = super()._get_stock_location_template()
        # Add sale price
        stock_location_template["6_sale_price_unit"] = {
            "header": {"value": "Unit Price"},
            "data": {
                "value": self._render("sale_price_unit"),
                "format": FORMATS["format_tcell_amount_right"],
            },
            "width": 20,
        }
        stock_location_template["7_sale_price"] = {
            "header": {"value": "Subtotal"},
            "data": {
                "value": self._render("sale_price"),
                "format": FORMATS["format_tcell_amount_right"],
            },
            "width": 20,
        }
        return stock_location_template

    def _get_render_space(self, index, line):
        render_space = super()._get_render_space(index, line)
        product_company = line.product_id.with_company(line.company_id)
        render_space["sale_price_unit"] = product_company.list_price
        render_space["sale_price"] = product_company.list_price * line.quantity
        return render_space

    def _write_footer_value_hook(self, results):
        dict_value_footer = super()._write_footer_value_hook(results)
        results.mapped("product_id.list_price")
        return dict_value_footer + [
            "",
            sum([result.product_id.list_price * result.quantity for result in results]),
        ]
