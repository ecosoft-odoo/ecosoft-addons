# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "etax.th"]

    def _get_branch_id(self):
        """
        By default, core odoo do not provide branch_id field in account.move and account.payment.
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
