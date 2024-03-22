# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _create_tax_cash_basis_moves_expense(self):
        """Allow post cash basis for set to_clear_tax=True
        and reset it back to draft"""
        moves = super()._create_tax_cash_basis_moves_expense()
        moves._post(soft=False)
        # EXPERIMENT: remove income / expense account move lines
        ml_groups = self.env["account.move.line"].read_group(
            domain=[("move_id", "in", moves.ids)],
            fields=[
                "move_id",
                "account_id",
                "debit",
                "credit",
            ],
            groupby=[
                "move_id",
                "account_id",
            ],
            lazy=False,
        )
        del_ml_groups = list(filter(lambda l: l["debit"] == l["credit"], ml_groups))
        account_ids = [g.get("account_id")[0] for g in del_ml_groups]
        # Not include taxes (0%)
        del_move_lines = moves.mapped("line_ids").filtered(
            lambda l: l.account_id.id in account_ids and not l.tax_line_id
        )
        if del_move_lines:
            self.env.cr.execute(
                "DELETE FROM account_move_line WHERE id in %s",
                (tuple(del_move_lines.ids),),
            )
        net_invoice_refund = self.env.context.get("net_invoice_refund")
        net_invoice_payment = self.env.context.get("net_invoice_payment")
        if not net_invoice_refund or net_invoice_payment:
            self._update_state_cash_basis(moves)
        # --
        return moves
