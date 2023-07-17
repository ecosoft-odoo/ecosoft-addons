# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("account_id", "asset_id", "product_id")
    def _compute_asset_profile(self):
        """Overwrite function _compute_asset_profile"""
        for rec in self:
            if rec.asset_id:
                rec.asset_profile_id = rec.asset_id.profile_id
            else:
                if rec.product_id and rec.product_id.asset_profile_id:
                    rec.asset_profile_id = rec.product_id.asset_profile_id
                elif rec.account_id.asset_profile_id:
                    rec.asset_profile_id = rec.account_id.asset_profile_id

    @api.onchange("asset_profile_id")
    def _onchange_asset_profile_id(self):
        """Overwrite function _onchange_asset_profile_id"""
        if self.account_id != self.asset_profile_id.account_asset_id:
            self.account_id = self.asset_profile_id.account_asset_id
