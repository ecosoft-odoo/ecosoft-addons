# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    purpose_code_id = fields.Many2one(
        comodel_name="etax.purpose.code",
        string="eTax Refund Reason",
    )
    credit_note_doctype_code_ids = fields.Many2many(
        comodel_name="etax.doctype.code",
        compute="_compute_credit_note_doctype_code_ids",
    )
    etax_status = fields.Char(
        compute="_compute_etax_status",
        string="eTax Status",
    )

    @api.depends("move_ids")
    def _compute_etax_status(self):
        etax_status = self.move_ids.mapped("etax_status")
        if len(etax_status) > 1:
            raise UserError(self.env._("All eTax Status should be same."))
        return self.write({"etax_status": etax_status[-1]})

    @api.depends("move_ids")
    def _compute_credit_note_doctype_code_ids(self):
        codes = (
            self.env["etax.doctype"]
            .search([("move_type", "=", "out_refund")])
            .mapped("doctype_code_id")
        )
        for rec in self:
            rec.credit_note_doctype_code_ids = codes

    @api.onchange("purpose_code_id")
    def _onchange_purpose_code_id(self):
        self.reason = self.purpose_code_id.reason

    def reverse_moves(self, is_modify=False):
        res = super().reverse_moves(is_modify)
        # Update Purpose code on Credit Note
        self.new_move_ids.write(
            {
                "create_purpose_code": self.purpose_code_id.code,
                "create_purpose": self.reason,
            }
        )
        return res
