# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    purpose_code_id = fields.Many2one(
        "purpose.code", string="Refund Reason", domain="[('is_credit_note', '=', True)]"
    )
    purpose_code = fields.Char()

    @api.onchange("purpose_code_id")
    def _onchange_purpose_code_id(self):
        if self.purpose_code_id:
            self.purpose_code = self.purpose_code_id.code
            self.reason = (
                (self.purpose_code_id.code != "CDNG99")
                and self.purpose_code_id.name
                or ""
            )

    def reverse_moves(self):
        res = super().reverse_moves()
        self.move_ids.mapped("reversal_move_id").write(
            {
                "create_purpose_code": self.purpose_code_id.code,
                "create_purpose": self.reason,
                "etax_move_type": "out_refund",
            }
        )
        return res
