# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, models, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "etax.th"]

    @api.depends('restrict_mode_hash_table', 'state')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        # If etax signed, user can't just reset to draft.
        # User need to create replacement invoice, do the update and submit eTax again.
        for move in self.filtered(lambda m: m.etax_status == 'success'):
            move.show_reset_to_draft_button = False

    def create_replacement_etax(self):
        """ Create replacement document and cancel the old one """
        self.ensure_one()
        if not (self.state == 'posted' and self.etax_status == 'success'):
            raise ValidationError(_("Only posted etax invoice can have a substitution"))
        res = self.copy_data()
        old_number = self.name
        suffix = '~R'
        if suffix in old_number:
            [number, rev] = old_number.split(suffix)
            res[0]["name"] = "%s%s%s" % (number, suffix, int(rev) + 1)
        else:
            res[0]["name"] = "%s%s%s" % (old_number, suffix, 1)
        res[0]["posted_before"] = self.posted_before
        res[0]["payment_reference"] = self.payment_reference
        res[0]["invoice_date"] = self.invoice_date
        res[0]["invoice_date_due"] = self.invoice_date_due
        move = self.create(res[0])
        self.button_draft()
        self.button_cancel()
        self.name = old_number  # Ensure name.
        return move
