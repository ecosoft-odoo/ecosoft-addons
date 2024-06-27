# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    request_document_id = fields.Many2one(
        comodel_name="request.document",
        readonly=True,
    )
