# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    @api.onchange("activity_id")
    def _onchange_activity_id(self):
        if self.activity_id:
            self.name = self.activity_id.name
