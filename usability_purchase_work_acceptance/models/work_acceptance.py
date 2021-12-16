# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    def _prepare_late_wa_move_line(self, name=False):
        move_line = super()._prepare_late_wa_move_line(name=name)
        move_line.update({"activity_id": self.env.company.wa_fines_late_activity_id})
        return move_line
