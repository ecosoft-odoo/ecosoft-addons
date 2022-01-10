# Copyright 2022 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class WithHoldingTaxReport(models.TransientModel):
    _inherit = "withholding.tax.report"

    income_tax_form = fields.Selection(
        selection_add=[("pnd54", "PND54"),],
        ondelete={"pnd54": "cascade"},
    )

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.income_tax_form == "pnd54":
            date_format = self.format_date()
            return "WHT-P54-{}".format(date_format)
        else:
            super()._get_report_base_filename()
