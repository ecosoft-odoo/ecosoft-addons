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
            return self.branch_id

    def _prepare_inet_data(self, form_type="", form_name=""):
        res = super()._prepare_inet_data()
        branch_id = self._get_branch_id()
        if branch_id:
            res.update({"c02_seller_branch_id": branch_id.name})
        if self.create_purpose_code:
            res.update(
                {
                    "h05_create_purpose_code": self.create_purpose_code,
                    "h06_create_purpose": self.create_purpose,
                }
            )
        return res
