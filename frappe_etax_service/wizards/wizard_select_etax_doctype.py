# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class WizardSelectEtaxDoctype(models.TransientModel):
    _name = "wizard.select.etax.doctype"

    doc_name_template = fields.Many2one(
        string="Invoice template",
        comodel_name="doc.type",
    )
    etax_move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("out_invoice_debit", "Customer Debit Note"),
        ],
        string="Type",
    )

    def sign_etax_invoice(self):
        active_id = self.env.context.get("active_ids", False)
        invoice = self.env["account.move"].browse(active_id)
        invoice.update(
            {
                "etax_doctype": self.doc_name_template.doctype_code,
                "is_send_frappe": True,
            }
        )
        form_type = self.doc_name_template.doc_source_template
        form_name = self.doc_name_template.name
        invoice.sign_etax(form_type=form_type, form_name=form_name)
        invoice.update({"is_send_frappe": False})
