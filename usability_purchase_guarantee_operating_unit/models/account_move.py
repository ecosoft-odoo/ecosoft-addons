# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("guarantee_ids")
    def _onchange_guarantee_ids(self):
        super()._onchange_guarantee_ids()
        for rec in self.filtered("guarantee_ids"):
            rec.operating_unit_id = rec.guarantee_ids[0].operating_unit_id.id
