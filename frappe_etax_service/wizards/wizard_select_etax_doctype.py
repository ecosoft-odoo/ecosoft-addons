# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import UserError


class WizardSelectEtaxDoctype(models.TransientModel):
    _name = "wizard.select.etax.doctype"
    _inherit = "etax.th"

    doc_name_template = fields.Many2one(
        string="Invoice template",
        comodel_name="ir.actions.report",
        domain=[("model", "=", "account.move"), ("binding_model_id", "!=", False)],
    )

    def _get_doctype_code(self, form_name=False):
        doctype = self.env["doc.type"].search([("doc_name_template", "=", form_name)])
        if doctype:
            return doctype

    def sign_etax_invoice(self):
        active_id = self.env.context.get("active_ids", False)
        doctype = self._get_doctype_code(form_name=self.doc_name_template.name)
        if not doctype:
            raise UserError(_("This invoice form does not set doctype code."))
        invoice = self.env["account.move"].browse(active_id)
        invoice.update({"etax_doctype": doctype.doctype_code})
        form_type = doctype.doc_source_template
        form_name = self.doc_name_template.name
        invoice.sign_etax(form_type=form_type, form_name=form_name)
