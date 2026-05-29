# Copyright 2026 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
        help="Domain evaluated against active records to determine if this report "
        "appears in the print wizard. Leave empty to always show.",
    )
