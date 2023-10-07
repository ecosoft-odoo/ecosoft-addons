# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "etax.th"]

    def _update_created_purpose(self, doc):
        # if it's credit note
        # if it's debit note
        pass

    def _get_branch_id(self):
        """
        By default, core odoo do not provide branch_id field in account.move and account.payment.
        This method will check if branch_id is exist in model and return branch_id
        """
        if "branch_id" in self.env["account.move"]._fields:
            return self.branch_id

    def _prepare_inet_data(self, form_type="", form_name=""):
        res = super()._prepare_inet_date()
        branch_id = self._get_branch_id()
        if branch_id:
            res.update({"c02_seller_branch_id": branch_id})
        return res
