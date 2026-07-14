# Copyright 2026 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class BasePrintWizard(models.TransientModel):
    _name = "base.print.wizard"
    _description = "Base Print Wizard"

    active_model = fields.Char(
        default=lambda self: self.env.context.get("active_model"),
    )
    available_doctype_ids = fields.Many2many(
        comodel_name="ir.actions.report",
        compute="_compute_available_doctype_ids",
        string="Available Reports",
    )
    doctype = fields.Many2one(
        comodel_name="ir.actions.report",
        domain="[('id', 'in', available_doctype_ids)]",
        default=lambda self: self._get_doctype_default(),
        required=True,
    )

    @api.depends("active_model")
    def _compute_available_doctype_ids(self):
        for rec in self:
            rec.available_doctype_ids = [
                fields.Command.set(rec._get_available_report_ids())
            ]

    def _get_available_report_ids(self):
        """Return IDs of reports applicable to the current active records.
        Reports with empty domain_form always qualify.
        Reports with domain_form are evaluated against active records.
        """
        active_model = self.env.context.get("active_model") or self.active_model
        active_ids = self.env.context.get("active_ids", [])
        if not active_model:
            return []
        if active_model not in self.env:
            return []
        records = self.env[active_model].browse(active_ids).exists()
        all_reports = self.env["ir.actions.report"].search(
            [("model", "=", active_model), ("show_in_wizard", "=", True)]
        )
        valid_ids = []
        for report in all_reports:
            if report.groups_id and not (report.groups_id & self.env.user.groups_id):
                continue
            if not report.domain_form:
                valid_ids.append(report.id)
            elif records:
                domain = report._get_wizard_domain()
                if records.filtered_domain(domain) == records:
                    valid_ids.append(report.id)
        return valid_ids

    @api.model
    def _get_doctype_default(self):
        """Auto-select when only one report is available. Override for fixed default."""
        ids = self._get_available_report_ids()
        return ids[0] if len(ids) == 1 else False

    def _get_action_report(self):
        active_ids = self.env.context.get("active_ids", False)
        model = self.env.context.get("active_model") or self.active_model
        if not model or model not in self.env:
            raise UserError(
                self.env._("No valid active model was provided for printing.")
            )
        return self.env[model].browse(active_ids).exists()

    def _get_report_context(self):
        """Return extra context dict forwarded to the report action.
        Override to add module-specific keys.
        """
        return {}

    def _validate_report(self):
        """Ensure the selected report is valid outside the form-view domain too."""
        self.ensure_one()
        active_model = self.env.context.get("active_model") or self.active_model
        if not active_model or active_model not in self.env:
            raise UserError(
                self.env._("No valid active model was provided for printing.")
            )
        if self.doctype.model != active_model:
            raise UserError(
                self.env._("The selected report does not match the active model.")
            )
        if self.doctype.id not in self._get_available_report_ids():
            raise UserError(
                self.env._(
                    "The selected report is not available for all selected records."
                )
            )

    def action_print(self):
        self.ensure_one()
        self._validate_report()
        objs = self._get_action_report()
        return self.doctype.with_context(**self._get_report_context()).report_action(
            objs
        )
