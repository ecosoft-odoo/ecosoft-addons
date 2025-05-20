# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    request_order_ids = fields.Many2many(
        comodel_name="request.order", string="Requests"
    )
    model = fields.Selection(
        selection_add=[
            ("request.order", "Request Order"),
            ("request.document", "Request Document"),
        ],
        ondelete={"request.order": "cascade", "request.document": "cascade"},
    )
