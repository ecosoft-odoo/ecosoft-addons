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
            ("entry", "Customer Payment"),
        ],
        string="Type",
    )
    run_background = fields.Boolean()

    def default_get(self, fields):
        res = super().default_get(fields)
        res_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        moves = self.env[res_model].browse(active_ids)
        move_type = list(set(moves.mapped("move_type")))
        is_debit = list(set(moves.mapped(lambda l: l.debit_origin_id and True or False)))
        template = moves.mapped("doc_name_template")
        template = False if len(template) > 1 else template
        if len(move_type) > 1 or len(is_debit) > 1:
            raise ValidationError(_("Multiple move types not allowed"))
        move_type = move_type and move_type[0] or False
        is_debit = is_debit and is_debit[0] or False
        if move_type == "out_invoice" and is_debit:
            move_type = "out_invoice_debit"
        res.update({
            "move_type": move_type,
            "doc_name_template": template.id,
            "run_background": len(moves) > 1
        })
        # Validation
        if move_type not in ["entry", "out_invoice", "out_refund", "out_invoice_debit"]:
            raise ValidationError(_("Only customer invoice can sign eTax"))
        return res

    def sign_etax_invoice(self):
        res_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", False)
        moves = self.env[res_model].browse(active_ids)
        self.pre_etax_validate(moves)
        for move in moves:
            move.update(
                {
                    "etax_doctype": self.doc_name_template.doctype_code,
                    "doc_name_template": self.doc_name_template,
                    "is_send_frappe": True,
                }
            )
            if self.run_background:
                move.etax_status = "to_process"
            else:
                move.sign_etax()

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
            lambda l: l.move_type in ["inv_invoice", "inv_refund"]
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
                _("%s has no tax invoice") % ", ".join(invalid.mapped("name")))
