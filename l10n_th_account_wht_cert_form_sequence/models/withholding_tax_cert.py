# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class WithholdingTaxCert(models.Model):
    _inherit = "withholding.tax.cert"
    _rec_name = "number"

    number = fields.Char(
        string="WHT Number",
        required=True,
        default="/",
        readonly=True,
        copy=False,
    )

    def _get_report_base_filename(self):
        if self.number and self.number != "/":
            return _("WHT Certificates - {}").format(self.number.replace("/", "_"))
        return super()._get_report_base_filename()

    def action_done(self):
        res = super().action_done()
        IrSequenceOptionLine = self.env["ir.sequence.option.line"]
        for rec in self:
            if rec.number in [False, "/"]:
                seq = IrSequenceOptionLine.get_sequence(rec)
                rec.number = seq.next_by_id()
        return res
