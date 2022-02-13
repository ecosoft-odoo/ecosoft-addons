# Copyright 2022 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class RdWithHoldingTaxReportWizard(models.TransientModel):
    _name = "rd.withholding.tax.report.wizard"
    _description = "RD Withholding Tax Report Wizard"

    income_tax_form = fields.Selection(
        selection=[
            ("pnd1", "PND1"),
            ("pnd1a", "PND1A"),
            ("pnd3", "PND3"),
            ("pnd53", "PND53"),
        ],
        string="Income Tax Form",
        required=True,
    )
    date_range_id = fields.Many2one(
        comodel_name="date.range", string="Date Range", required=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        domain=lambda self: self._get_domain_company_id(),
        string="Company",
        required=True,
        ondelete="cascade",
    )

    def _get_domain_company_id(self):
        selected_companies = self.env["res.company"].browse(
            self.env.context.get("allowed_company_ids")
        )
        return [("id", "in", selected_companies.ids)]

    def button_export_pdf(self):
        self.ensure_one()
        report_type = "qweb-pdf"
        return self._export(report_type)

    def _prepare_wht_report(self):
        self.ensure_one()
        return {
            "income_tax_form": self.income_tax_form,
            "date_range_id": self.date_range_id.id,
            "date_from": self.date_range_id.date_start,
            "date_to": self.date_range_id.date_end,
            "company_id": self.company_id.id,
        }

    def _export(self, report_type):
        """Default export is PDF."""
        model = self.env["rd.withholding.tax.report"]
        report = model.create(self._prepare_wht_report())
        return report.print_report(report_type)
