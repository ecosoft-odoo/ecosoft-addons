# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids
        moves._check_move_reconciled(action="reset to draft / reverse")
        res = super().reverse_moves()
        # Overwite payment state to reversed
        moves.with_context(bypass_lockdate=1).write({"payment_state": "reversed"})
        return res
