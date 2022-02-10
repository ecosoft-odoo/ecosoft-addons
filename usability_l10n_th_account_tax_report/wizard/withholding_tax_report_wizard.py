# Copyright 2022 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class WithHoldingTaxReportWizard(models.TransientModel):
    _inherit = "withholding.tax.report.wizard"

    income_tax_form = fields.Selection(
        selection_add=[
            ("pnd54", "PND54"),
        ],
        ondelete={"pnd54": "cascade"},
    )
