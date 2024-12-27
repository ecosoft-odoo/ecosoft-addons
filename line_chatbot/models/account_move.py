# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "base.line.process"]

    # NOTE: This is a simple example, in real case, you may want to add more
    def action_post(self):
        self.message_line_push(
            f"Invoice number {self.name} has been posted",
            self.env.user.line_access_token,
        )
        return super().action_post()
