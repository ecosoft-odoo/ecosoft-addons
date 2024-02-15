# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.translate import _


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    is_full_tax = fields.Boolean()
    full_tax_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain=[("type", "=", "sale")],
        string="Use Specific Journal",
        compute="_compute_full_tax_journal_id",
        readonly=False,
        store=True,
        check_company=True,
        help="uses the full tax journal for new draft.",
    )

    @api.depends("is_full_tax")
    def _compute_full_tax_journal_id(self):
        full_tax_journal_id = self.env.ref(
            "account_move_full_tax_invoice.account_full_tax_journal"
        )
        for rec in self:
            if rec.is_full_tax:
                rec.full_tax_journal_id = full_tax_journal_id

    def reverse_moves(self):
        """Must overwrite function because it can't hooks anyway"""
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [
                self.env["account.move"],
                [],
                True,
            ],  # Moves to be cancelled by the reverses.
            [self.env["account.move"], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = default_vals.get("auto_post") != "no"
            is_cancel_needed = not is_auto_post and self.refund_method in (
                "cancel",
                "modify",
            )
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env["account.move"]
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(
                default_values_list, cancel=is_cancel_needed
            )
            if self.refund_method == "modify" or self.is_full_tax:
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    move_data = move.copy_data(
                        {"date": self.date if self.date_mode == "custom" else move.date}
                    )[0]
                    if self.is_full_tax:
                        move_data["journal_id"] = self.full_tax_journal_id.id
                        move_data["origin_invoice_ftx_move_id"] = move.id
                    moves_vals_list.append(move_data)
                new_moves = self.env["account.move"].create(moves_vals_list)
            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect
        # Create action.
        action = {
            "name": _("Reverse Moves"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
        }
        if len(moves_to_redirect) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": moves_to_redirect.id,
                    "context": {"default_move_type": moves_to_redirect.move_type},
                }
            )
        else:
            action.update(
                {
                    "view_mode": "tree,form",
                    "domain": [("id", "in", moves_to_redirect.ids)],
                }
            )
            if len(set(moves_to_redirect.mapped("move_type"))) == 1:
                action["context"] = {
                    "default_move_type": moves_to_redirect.mapped("move_type").pop()
                }
        return action
