# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    name_snapshot = fields.Char()
    address_snapshot = fields.Char()

    def _post(self, soft=True):
        for record in self:
            if not record.name_snapshot:
                record.name_snapshot = record.partner_id.display_name
            if not record.address_snapshot:
                record.address_snapshot = record.partner_id._display_address(
                    without_company=True
                )
        return super()._post(soft)
