# Copyright 2026 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


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
        records = self.env[active_model].browse(active_ids)
        all_reports = self.env["ir.actions.report"].search(
            [("model", "=", active_model), ("show_in_wizard", "=", True)]
        )
        valid_ids = []
        for report in all_reports:
            if not report.domain_form:
                valid_ids.append(report.id)
            elif active_ids:
                domain = safe_eval(report.domain_form)
                if records.filtered_domain(domain):
                    valid_ids.append(report.id)
        return valid_ids

    @api.model
    def _get_doctype_default(self):
        """Auto-select when only one report is available. Override for fixed default."""
        ids = self._get_available_report_ids()
        return ids[0] if len(ids) == 1 else False

    def _get_action_report(self):
        active_ids = self._context.get("active_ids", False)
        model = self._context.get("active_model") or self.active_model
        objs = self.env[model].browse(active_ids)
        return objs

    def action_print(self):
        self.ensure_one()
        objs = self._get_action_report()
        return self.doctype.report_action(objs)
