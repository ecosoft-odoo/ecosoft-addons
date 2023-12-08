# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "etax.th"]

    def action_draft(self):
        if self.filtered(
            lambda l: l.etax_status in ("success", "processing", "to_process")
        ):
            raise ValidationError(
                _(
                    "Cannot reset to draft, eTax submission already started or succeeded.\n"
                    "You should do the refund process instead."
                )
            )
        return super().action_draft()

    def _get_branch_id(self):
        """
        By default, core odoo do not provide branch_id field in
        account.move and account.payment.
        This method will check if branch_id is exist in model and return branch_id
        """
        if self.reconciled_invoice_ids:
            if "branch_id" in self.env["account.move"]._fields:
                return self.reconciled_invoice_ids[0].branch_id.name
        else:
            return False
