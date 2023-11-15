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
    move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("out_invoice_debit", "Customer Debit Note"),
        ],
        string="Type",
    )
    run_background = fields.Boolean()

    def default_get(self, fields):
        res = super().default_get(fields)
        active_ids = self.env.context.get("active_ids")
        invoices = self.env["account.move"].browse(active_ids)
        move_type = list(set(invoices.mapped("move_type")))
        template = invoices.mapped("doc_name_template")
        template = False if len(template) > 1 else template
        if len(move_type) > 1:
            raise ValidationError(_("Multiple move types not allowed"))
        move_type = move_type and move_type[0] or False
        res.update({
            "move_type": move_type,
            "doc_name_template": template.id,
            "run_background": len(invoices) > 1
        })
        # Validation
        if move_type not in ["out_invoice", "out_refund", "out_invoice_debit"]:
            raise ValidationError(_("Only customer invoices can sign eTax"))
        return res

    def sign_etax_invoice(self):
        active_ids = self.env.context.get("active_ids", False)
        invoices = self.env["account.move"].browse(active_ids)
        self.pre_etax_validate(invoices)
        for invoice in invoices:
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

    def pre_etax_validate(self, invoices):
        # Already under processing or succeed
        invalid = invoices.filtered(
            lambda l: l.etax_status in ["success", "processing"]
        )
        if invalid:
            raise ValidationError(
                _("%s, eTax status is in Processing/Success") %
                ", ".join(invalid.mapped("name"))
            )
        # Not in valid customer invoice type
        invalid = invoices.filtered(
            lambda l: l.etax_status in ["entry", "inv_invoice", "inv_refund"]
        )
        if invalid:
            raise ValidationError(
                _("%s move_type not valid\nOnly customer invoices can sign eTax") %
                ", ".join(invalid.mapped("name"))
            )
        # Not posted
        invalid = invoices.filtered(lambda l: l.state != "posted")
        if invalid:
            raise ValidationError(
                _("Some invoices are not posted and cannot sign eTax")
            )
        # No tax invoice
        invalid = invoices.filtered(lambda l: not l.tax_invoice_ids)
        if invalid:
            raise ValidationError(
                _("%s has not tax") % ", ".join(invalid.mapped("name")))
