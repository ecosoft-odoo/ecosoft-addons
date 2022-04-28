# Copyright 2022 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, fields, models
from odoo.exceptions import UserError


class WithholdingTaxCert(models.Model):
    _inherit = "withholding.tax.cert"

    income_tax_form = fields.Selection(
        selection_add=[
            ("pnd54", "PND54"),
        ],
        ondelete={"pnd54": "cascade"},
    )

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.income_tax_form == "pnd54":
            raise UserError(_("PND54 cannot print WHT Certificates."))
        return super()._get_report_base_filename()

    def action_done(self):
        for rec in self:
            if rec.income_tax_form != "pnd54":
                if any(not line.wht_cert_income_type for line in rec.wht_line):
                    raise UserError(
                        _("Please select Type of Income on every withholding moves.")
                    )
        return super().action_done()


class WithholdingTaxCertLine(models.Model):
    _inherit = "withholding.tax.cert.line"

    wht_cert_income_type = fields.Selection(required=False)
    income_tax_form = fields.Selection(related="cert_id.income_tax_form")
