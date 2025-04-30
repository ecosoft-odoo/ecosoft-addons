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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("request.order") or "/"
                )
        return super().create(vals_list)

    def action_submit(self):
        return self.write({"state": "submit"})

    def action_approve(self):
        return self.write({"state": "approve"})

    def action_done(self):
        return self.write({"state": "done"})

    def action_create_document(self):
        """Hook method to create document"""
        for rec in self:
            for line in rec.line_ids:
                getattr(line, f"_create_{line.request_type}")()
        return self.action_done()

    def action_cancel(self):
        return self.write({"state": "cancel"})

    def action_draft(self):
        return self.write({"state": "draft"})
