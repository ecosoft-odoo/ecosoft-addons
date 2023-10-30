# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class WizardSelectEtaxDoctype(models.TransientModel):
    _name = "wizard.select.etax.doctype"

    doc_name_template = fields.Many2one(
        string="Invoice template",
        comodel_name="doc.type",
        required=True,
    )
    etax_move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("out_invoice_debit", "Customer Debit Note"),
        ],
        string="Type",
    )
    run_background = fields.Boolean()

    def sign_etax_invoice(self):
        active_id = self.env.context.get("active_ids", False)
        invoice = self.env["account.move"].browse(active_id)
        if invoice.move_type not in ["out_invoice", "out_refund", "out_invoice_debit"]:
            raise ValidationError(_("Only customer invoices can sign eTax"))
        if invoice.etax_status in ["success", "processing"]:
            raise ValidationError(_("eTax status is in Processing/Success"))
        invoice.update(
            {
                "etax_doctype": self.doc_name_template.doctype_code,
                "doc_name_template": self.doc_name_template,
                "is_send_frappe": True,
            }
        )
        if self.run_background:
            invoice.etax_status = "to_process"
        else:
            invoice.sign_etax()
