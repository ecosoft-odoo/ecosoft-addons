# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class WizardSelectReplacementPurpose(models.TransientModel):
    _name = "wizard.select.replacement.purpose"

    purpose_code_id = fields.Many2one(
        comodel_name="purpose.code",
        string="Purpose",
        domain="[('is_replacement', '=', True)]",
        required=True,
    )
    reason = fields.Char(
        required=True,
    )

    @api.onchange("purpose_code_id")
    def _onchange_purpose_code_id(self):
        self.reason = self.purpose_code_id.reason

    def create_replacement(self):
        active_ids = self.env.context.get("active_ids", [])
        move = self.env["account.move"].browse(active_ids)
        move.ensure_one()
        replacement = move.create_replacement_etax()
        replacement.create_purpose_code = self.purpose_code_id.code
        replacement.create_purpose = self.reason
        replacement.replaced_entry_id = move
        return {
            "type": "ir.actions.act_window",
            "views": [(False, "form")],
            "view_mode": "form",
            "res_model": replacement._name,
            "res_id": replacement.id,
            "context": self.env.context,
        }

