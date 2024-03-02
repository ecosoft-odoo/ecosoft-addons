# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountFormWizard(models.TransientModel):
    _name = "account.form.wizard"
    _description = "Account Form Wizard"

    doctype = fields.Many2one(
        comodel_name="ir.actions.report",
        domain=lambda self: self._get_doctype_domain(),
        default=lambda self: self._get_doctype_default(),
        required=True,
    )

    def _get_domain_form(self):
        return [("model", "=", self.env.context.get("active_model"))]

    @api.model
    def _get_doctype_domain(self):
        domain = self._get_domain_form()
        return domain

    @api.model
    def _get_doctype_default(self):
        """Inherit this function for default form (if any)"""
        return False

    def _get_action_report(self):
        active_ids = self._context.get("active_ids", False)
        model = self._context.get("active_model", False)
        objs = self.env[model].browse(active_ids)
        return objs

    def action_print(self):
        self.ensure_one()
        objs = self._get_action_report()
        return self.doctype.report_action(objs)
