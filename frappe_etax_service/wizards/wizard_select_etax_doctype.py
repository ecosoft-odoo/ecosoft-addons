# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class WizardSelectEtaxDoctype(models.TransientModel):
    _name = "wizard.select.etax.doctype"
    _inherit = "etax.th"

    def _get_doctype_code(self, form_name=False):
        code = False
        doctype = self.env["doc.type"].search([("doc_name_template", "=", form_name)])
        if doctype:
            code = doctype.doctype_code
        return code

    def sign_etax_invoice(self):
        active_id = self.env.context.get("active_ids", False)
        doc_code = self._get_doctype_code(form_name=self.doc_name_template.name)
        if not doc_code:
            raise ValidationError(_("This invoice form does not set doctype code."))
        invoice = self.env["account.move"].browse(active_id)
        invoice.update({
            "etax_doctype": doc_code,
            "doc_name_template": self.doc_name_template,
        })
        # Set form type == 'odoo' maybe let user config this later
        form_type = "odoo"
        form_name = self.doc_name_template.name
        invoice.sign_etax(form_type=form_type, form_name=form_name)
