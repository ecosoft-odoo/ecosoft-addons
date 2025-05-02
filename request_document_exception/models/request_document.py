# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestDocument(models.Model):
    _name = "request.document"
    _inherit = ["request.document", "base.exception.method"]

    ignore_exception = fields.Boolean(
        related="request_id.ignore_exception", store=True, string="Ignore Exceptions"
    )

    @api.model
    def _reverse_field(self):
        return "request_order_ids"

    def _get_main_records(self):
        return self.mapped("request_id")

    def _detect_exceptions(self, rule):
        records = super()._detect_exceptions(rule)
        return records.mapped("request_id")
