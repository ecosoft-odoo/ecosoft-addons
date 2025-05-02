# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class RequestOrder(models.Model):
    _name = "request.order"
    _inherit = ["request.order", "base.exception"]

    @api.model
    def _reverse_field(self):
        return "request_order_ids"

    def detect_exceptions(self):
        all_exceptions = super().detect_exceptions()
        lines = self.mapped("line_ids")
        all_exceptions += lines.detect_exceptions()
        return all_exceptions

    @api.onchange("line_ids")
    def onchange_ignore_exception(self):
        if self.state == "submit":
            self.ignore_exception = False

    def action_submit(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_submit()

    @api.model
    def _get_popup_action(self):
        action = self.env.ref(
            "request_document_exception.action_request_exception_confirm"
        )
        return action

    def action_draft(self):
        res = super().action_draft()
        for rec in self:
            rec.exception_ids = False
            rec.main_exception_id = False
            rec.ignore_exception = False
        return res
