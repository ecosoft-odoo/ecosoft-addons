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

    def create_debit(self):
        res = super().create_debit()
        self.move_ids.mapped("debit_note_ids")[0].write(
            {
                "create_purpose_code": self.purpose_code_id.code,
                "create_purpose": self.reason,
            }
        )
        return res
