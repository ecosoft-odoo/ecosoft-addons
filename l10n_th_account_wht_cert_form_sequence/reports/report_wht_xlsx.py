# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import FORMATS


class WithholdingTaxReportXslx(models.AbstractModel):
    _inherit = "report.withholding.tax.report.xlsx"

    def _get_ws_params(self, wb, data, obj):
        ws_params = super()._get_ws_params(wb, data, obj)
        ws_params[0]["wanted_list"].append("12_number")
        ws_params[0]["col_specs"]["12_number"] = {
            "header": {"value": "Number"},
            "data": {"value": self._render("number")},
            "width": 19,
        }
        return ws_params

    def _write_ws_lines(self, row_pos, ws, ws_params, obj):
        """
        NOTE: V16 can hooks some method (Don't need to overwrite)
        Overwrite this method for adding render_spance value
        """
        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=FORMATS["format_theader_blue_center"],
        )
        ws.freeze_panes(row_pos, 0)
        index = 1
        for line in obj.results:
            cancel = line.cert_id.state == "cancel"
            row_pos = self._write_line(
                ws,
                row_pos,
                ws_params,
                col_specs_section="data",
                render_space={
                    "sequence": index,
                    "vat": line.cert_id.partner_id.vat or "",
                    "display_name": not cancel
                    and line.cert_id.partner_id.display_name
                    or "Cancelled",
                    "street": not cancel and line.cert_id.partner_id.street or "",
                    "date": line.cert_id.date,
                    "income_desc": line.wht_cert_income_desc or "",
                    "tax": line.wht_percent / 100 or 0.00,
                    "base_amount": not cancel and line.base or 0.00,
                    "tax_amount": not cancel and line.amount or 0.00,
                    "tax_payer": line.cert_id.tax_payer,
                    "payment_id": line.cert_id.name,
                    "number": line.cert_id.number,
                },
                default_format=FORMATS["format_tcell_left"],
            )
            index += 1
        return row_pos

    def _write_ws_footer(self, row_pos, ws, obj):
        """
        NOTE: V16 can hooks some method (Don't need to overwrite)
        Overwrite this method to add merge range + 1
        """
        results = obj.results.filtered(lambda res: res.cert_id.state == "done")
        ws.merge_range(row_pos, 0, row_pos, 6, "")
        ws.merge_range(row_pos, 9, row_pos, 11, "")  # change 10 to 11
        ws.write_row(
            row_pos, 0, ["Total Balance"], FORMATS["format_theader_blue_right"]
        )
        ws.write_row(
            row_pos,
            7,
            [sum(results.mapped("base")), sum(results.mapped("amount")), ""],
            FORMATS["format_theader_blue_amount_right"],
        )
        return row_pos
