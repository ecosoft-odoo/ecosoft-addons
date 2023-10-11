# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "etax.th"]

    def _get_branch_id(self):
        """
        By default, core odoo do not provide branch_id field in
        account.move and account.payment.
        This method will check if branch_id is exist in model and return branch_id
        """
        if "branch_id" in self.env["account.move"]._fields:
            return self.branch_id.name

    def _get_origin_inv_date(self):
        """
        In case of Credit note or Debit note, we need invoice date of origin invoice
        to fill in h08_additional_ref_issue_dtm
        """
        if self.debit_origin_id and self.debit_origin_id.invoice_date:
            return self.debit_origin_id.invoice_date.strftime("%Y-%m-%dT%H:%M:%S")

        if self.reversed_entry_id and self.reversed_entry_id.invoice_date:
            return self.reversed_entry_id.invoice_date.strftime("%Y-%m-%dT%H:%M:%S")

        if self.replaced_entry_id:
            return self.replaced_entry_id.invoice_date.strftime("%Y-%m-%dT%H:%M:%S")

    def _get_additional_amount(self):
        """
        In case of credit note, debit note or replacement tax invoice
        Get original untax amount for
            f36_original_total_amount = original_amount_untaxed
            f40_adjusted_information_amount = diff_amount_untaxed
            f38_line_total_amount = corrected_amount_untaxed
        """
        original_amount_untaxed = corrected_amount_untaxed = diff_amount_untaxed = False
        if self.debit_origin_id:
            original_amount_untaxed = self.debit_origin_id.amount_untaxed
            diff_amount_untaxed = self.amount_untaxed
            corrected_amount_untaxed = original_amount_untaxed + diff_amount_untaxed
        if self.reversed_entry_id:
            original_amount_untaxed = self.reversed_entry_id.amount_untaxed
            diff_amount_untaxed = self.amount_untaxed
            corrected_amount_untaxed = original_amount_untaxed - diff_amount_untaxed
        if self.replaced_entry_id:
            original_amount_untaxed = False
            diff_amount_untaxed = False
            corrected_amount_untaxed = self.amount_untaxed
        return (original_amount_untaxed, diff_amount_untaxed, corrected_amount_untaxed)

    @api.depends("restrict_mode_hash_table", "state")
    def _compute_show_reset_to_draft_button(self):
        res = super()._compute_show_reset_to_draft_button()
        # If etax signed, user can't just reset to draft.
        # User need to create replacement invoice, do the update and submit eTax again.
        for move in self.filtered(lambda m: m.etax_status == "success"):
            move.show_reset_to_draft_button = False
        return res

    def create_replacement_etax(self):
        """Create replacement document and cancel the old one"""
        self.ensure_one()
        if not (self.state == "posted" and self.etax_status == "success"):
            raise ValidationError(_("Only posted etax invoice can have a substitution"))
        res = self.copy_data()
        old_number = self.name
        suffix = "~R"
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
