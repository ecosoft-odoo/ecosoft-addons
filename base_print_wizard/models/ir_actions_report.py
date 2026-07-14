# Copyright 2026 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    show_in_wizard = fields.Boolean(
        string="Show in Print Wizard",
        default=False,
        help="If enabled, this report appears in the base print wizard. "
        "Use this instead of binding_model_id for reports accessed only via wizard.",
    )
    domain_form = fields.Char(
        string="Wizard Domain",
        help="Domain evaluated against every active record to determine if this report "
        "appears in the print wizard. Leave empty to always show.",
    )

    def _get_wizard_domain(self):
        self.ensure_one()
        if not self.domain_form:
            return []
        try:
            domain = safe_eval(self.domain_form)
            expression.normalize_domain(domain)
        except (AssertionError, NameError, SyntaxError, TypeError, ValueError) as error:
            raise ValidationError(
                self.env._(
                    "Invalid Wizard Domain on report %(report)s: %(error)s",
                    report=self.display_name,
                    error=error,
                )
            ) from error
        return domain

    @api.constrains("domain_form")
    def _check_domain_form(self):
        for report in self.filtered("domain_form"):
            report._get_wizard_domain()
