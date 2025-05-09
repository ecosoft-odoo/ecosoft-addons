# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestDocument(models.Model):
    _name = "request.document"
    _description = "Request Document"

    request_id = fields.Many2one(
        comodel_name="request.order",
        index=True,
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        compute="_compute_name_document",
        store=True,
        string="Reference",
    )
    name_document = fields.Char(
        string="Document",
        compute="_compute_document",
        store=True,
    )
    total_amount_request = fields.Monetary()
    total_amount_document = fields.Monetary(
        compute="_compute_document",
        store=True,
    )
    request_type = fields.Selection(
        selection=[],
        required=True,
    )
    state = fields.Selection(
        related="request_id.state",
        store=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id",
        store=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        store=True,
        readonly=False,
    )

    @api.depends("company_id")
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id

    @api.depends("request_id")
    def _compute_name_document(self):
        for rec in self:
            if rec.id:
                rec.name = f"{rec.request_id.name} - {rec.id}"

    def open_request_document(self):
        return

    def _compute_document(self):
        for rec in self:
            rec.name_document = ""
            rec.total_amount_document = 0.0
