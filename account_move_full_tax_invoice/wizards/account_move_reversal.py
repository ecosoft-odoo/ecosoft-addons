# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    is_full_tax = fields.Boolean()
    full_tax_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain=[("type", "=", "sale")],
        string="Use Specific Journal Full Tax",
        compute="_compute_full_tax_journal_id",
        readonly=False,
        store=True,
        check_company=True,
        help="uses the full tax journal for new draft.",
    )

    @api.onchange("is_full_tax")
    def _onchange_full_tax(self):
        if self.is_full_tax:
            self.refund_method = "modify"
            self.date = self.move_ids.invoice_date

    @api.depends("is_full_tax")
    def _compute_full_tax_journal_id(self):
        full_tax_journal_id = self.env.ref(
            "account_move_full_tax_invoice.account_full_tax_journal"
        )
        for rec in self:
            if rec.is_full_tax:
                rec.full_tax_journal_id = full_tax_journal_id

    def reverse_moves(self):
        action = super().reverse_moves()
        if self.is_full_tax:
            self.move_ids.write({"move_full_tax_id": action["res_id"]})
        return action
