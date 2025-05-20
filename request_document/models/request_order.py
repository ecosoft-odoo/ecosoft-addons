# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestOrder(models.Model):
    _name = "request.order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Request Order"
    _check_company_auto = True
    _order = "name desc"

    name = fields.Char(
        default="/",
        readonly=True,
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="company_id.currency_id"
    )
    line_ids = fields.One2many(
        comodel_name="request.document",
        inverse_name="request_id",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submit", "Submitted"),
            ("approve", "Approved"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    total_amount_document = fields.Monetary(
        compute="_compute_total_amount",
        store=True,
        tracking=True,
    )
    total_amount_request = fields.Monetary(
        compute="_compute_total_amount",
        store=True,
        tracking=True,
    )

    @api.depends("line_ids.total_amount_document", "line_ids.total_amount_request")
    def _compute_total_amount(self):
        for rec in self:
            request_document = rec.line_ids
            rec.total_amount_document = sum(
                request_document.mapped("total_amount_document")
            )
            rec.total_amount_request = sum(
                request_document.mapped("total_amount_request")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("request.order") or "/"
                )
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            for line in rec.line_ids:
                line.total_amount_request = line.total_amount_document
        return self.write({"state": "submit"})

    def action_approve(self):
        return self.write({"state": "approve"})

    def action_done(self):
        return self.write({"state": "done"})

    def action_process_document(self):
        """Hook method to process document"""
        for rec in self:
            for line in rec.line_ids:
                getattr(line, f"_create_{line.request_type}")()
        return self.action_done()

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def action_draft(self):
        return self.write({"state": "draft"})
