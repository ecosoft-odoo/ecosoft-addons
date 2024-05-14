# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import logging

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
    FORMATS,
    XLS_HEADERS,
)

_logger = logging.getLogger(__name__)


class ReportStockInventoryXlsx(models.TransientModel):
    _name = "report.stock_report_xlsx.report_stock_inventory_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Stock Inventory Report Excel"

    def _define_formats(self, workbook):
        res = super()._define_formats(workbook)
        date_format = "DD/MM/YYYY"
        FORMATS["format_date_dmy_right"] = workbook.add_format(
            {"align": "right", "num_format": date_format}
        )
        return res

    def _get_stock_inventory_template(self):
        return {
            "1_index": {
                "header": {"value": "#"},
                "data": {"value": self._render("index")},
                "width": 5,
            },
            "2_location_name": {
                "header": {"value": "Location"},
                "data": {"value": self._render("location_name")},
                "width": 25,
            },
            "3_product_code": {
                "header": {"value": "Code"},
                "data": {"value": self._render("product_code")},
                "width": 15,
            },
            "4_product_name": {
                "header": {"value": "Product Name"},
                "data": {
                    "value": self._render("product_name"),
                },
                "width": 35,
            },
            "5_quantity": {
                "header": {"value": "Quantity"},
                "data": {
                    "value": self._render("quantity"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
        }

    def _get_ws_params(self, wb, data, objects):
        stock_inventory_template = self._get_stock_inventory_template()
        ws_params = {
            "ws_name": "Stock Inventory Report",
            "generate_ws_method": "_stock_inventory_report",
            "title": "Stock Inventory Report",
            "wanted_list": [k for k in sorted(stock_inventory_template.keys())],
            "col_specs": stock_inventory_template,
        }
        return [ws_params]

    def _write_ws_header(self, row_pos, ws, data_list):
        for data in data_list:
            ws.merge_range(row_pos, 0, row_pos, 2, "")
            ws.write_row(row_pos, 0, [data[0]], FORMATS["format_theader_blue_center"])
            ws.merge_range(row_pos, 3, row_pos, 5, "")
            ws.write_row(row_pos, 3, [data[1]], FORMATS["format_tcell_left"])
            row_pos += 1
        return row_pos + 1

    def _get_render_space(self, index, line):
        return {
            "index": index,
            "location_name": line.location_id.name,
            "product_code": line.product_id.default_code or "",
            "product_name": line.product_id.name or "",
            "quantity": line.quantity or 0.00,
        }

    def _write_ws_lines(self, row_pos, ws, ws_params, objects):
        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=FORMATS["format_theader_blue_left"],
        )
        ws.freeze_panes(row_pos, 0)
        default_format = FORMATS["format_tcell_left"]
        row_pos = max(
            [
                self._write_line(
                    ws,
                    row_pos + index,
                    ws_params,
                    col_specs_section="data",
                    render_space=self._get_render_space(index + 1, line),
                    default_format=default_format,
                )
                for index, line in enumerate(objects.results)
            ]
        )
        return row_pos

    def _write_footer_value_hook(self, results):
        return [
            sum(results.mapped("quantity")),
        ]

    def _write_ws_footer(self, row_pos, ws, ws_params, objects):
        results = objects.results
        col_end = ws_params["wanted_list"].index("4_product_name")
        ws.merge_range(row_pos, 0, row_pos, col_end, "")
        ws.write_row(row_pos, 0, ["Total"], FORMATS["format_theader_blue_right"])
        ws.write_row(
            row_pos,
            col_end + 1,
            self._write_footer_value_hook(results),
            FORMATS["format_theader_blue_amount_right"],
        )
        return row_pos

    def _stock_inventory_report(self, wb, ws, ws_params, data, objects):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
        ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])
        self._set_column_width(ws, ws_params)
        row_pos = 0
        header_data_list = self._get_header_data_list(objects)
        row_pos = self._write_ws_title(ws, row_pos, ws_params, merge_range=True)
        row_pos = self._write_ws_header(row_pos, ws, header_data_list)
        row_pos = self._write_ws_lines(row_pos, ws, ws_params, objects)
        row_pos = self._write_ws_footer(row_pos, ws, ws_params, objects)

    def _get_header_data_list(self, objects):
        return [
            ("Company", objects.company_id.display_name or "-"),
            (
                "Location(s)",
                ", ".join(objects.location_ids.mapped("display_name")) or "All",
            ),
            (
                "Product(s)",
                ", ".join(objects.product_ids.mapped("display_name")) or "All",
            ),
        ]
