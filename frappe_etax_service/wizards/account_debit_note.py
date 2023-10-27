# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class AccountDebitNote(models.TransientModel):
    _inherit = "account.debit.note"

    purpose_code_id = fields.Many2one(
        "purpose.code", string="Refund Reason", domain="[('is_debit_note', '=', True)]"
    )
    purpose_code = fields.Char()

    @api.onchange("purpose_code_id")
    def _onchange_purpose_code_id(self):
        if self.purpose_code_id:
            self.purpose_code = self.purpose_code_id.code
            self.reason = (
                (self.purpose_code_id.code != "DBNG99")
                and self.purpose_code_id.name
                or ""
            )

    def _prepare_default_values(self, move):
        default_values = super()._prepare_default_values(move)
        default_values.update(
            {
                "create_purpose_code": self.purpose_code_id.code,
                "create_purpose": self.reason,
                "etax_move_type": "out_invoice_debit",
            }
        )
        return default_values
