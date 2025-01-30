# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "line.service"]

    # NOTE: This is a simple example, in real case, you may want to add more
    def action_post(self):
        for rec in self:
            # Add log and send to line
            message_list = [
                {
                    "type": "text",
                    "text": f"Invoice number {rec.name} has been posted",
                }
            ]
            rec.message_post(
                body=message_list,
                message_type="line",
                line_partner_ids=rec.partner_id.ids,
            )
        return super().action_post()
