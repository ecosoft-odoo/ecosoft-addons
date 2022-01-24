# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _update_moveline_operating_unit(self, payments, payment, reconciled_moves):
        """ Update OU in all move line """
        res = super()._update_moveline_operating_unit(
            payments, payment, reconciled_moves
        )
        move = payment.move_id
        for line in move.line_ids.filtered(lambda l: not l.operating_unit_id):
            line.write(
                {
                    "operating_unit_id": reconciled_moves.operating_unit_id.id,
                }
            )
        return res
