# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveTemplateRun(models.TransientModel):
    _inherit = "account.move.template.run"

    def _prepare_move(self):
        move_vals = super()._prepare_move()
        move_vals["scrap_id"] = self.env.context.get("scrap_id")
        return move_vals
