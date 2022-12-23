# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "tier.validation"]
    _state_field = "state"
    _state_from = ["posted"]

    _tier_validation_manual_config = False

    def action_draft(self):
        """Clear tier validation if set to draft"""
        if not self._context.get("skip_clear_tier_validation", False):
            self.mapped("review_ids").unlink()
        return super().action_draft()

    def action_cancel(self):
        """Clear tier validation if set to cancel"""
        if not self._context.get("skip_clear_tier_validation", False):
            self.mapped("review_ids").unlink()
        return super().action_cancel()
