# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class RequestExceptionConfirm(models.TransientModel):
    _name = "request.exception.confirm"
    _description = "Request exception wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one(comodel_name="request.order", string="Request")

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        return super().action_confirm()
