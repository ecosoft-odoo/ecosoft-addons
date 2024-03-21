# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    move_full_tax_id = fields.Many2one(
        comodel_name="account.move",
        copy=False,
        readonly=True,
        string="Invoice Full Tax",
    )
    is_tax_abb = fields.Boolean(
        string="Tax (ABB)",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", "=", False)]},
    )

    def _get_update_value(self, move_full_tax):
        return {
            "invoice_date": self.invoice_date,
            "journal_id": self.env.ref(
                "account_move_tax_abb.account_full_tax_journal"
            ).id,
        }

    def action_convert_to_full_tax(self):
        for rec in self:
            if not rec.is_tax_abb:
                raise UserError(
                    _("Cannot convert to full tax invoice. please check document.")
                )
            # Create new invoice with copy from origin
            move_full_tax = rec.copy()
            dict_update_value = rec._get_update_value(move_full_tax)
            move_full_tax.write(dict_update_value)
            # Link origin and full tax
            rec.write({"move_full_tax_id": move_full_tax.id})
            # Cancel origin
            rec.button_cancel()
        return
