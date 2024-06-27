# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestRequest(models.Model):
    _name = "request.request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Request Header"
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
        readonly=True,
        states={"draft": [("readonly", False)]},
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
                    self.env["ir.sequence"].next_by_code("request.request") or "/"
                )
        return super().create(vals_list)

    def action_submit(self):
        self.write({"state": "submit"})
        return True

    def action_approve(self):
        self.write({"state": "approve"})
        return True

    def action_done(self):
        self.write({"state": "done"})
        return True

    def action_create_document(self):
        """Hook method to create document"""
        for rec in self:
            for line in rec.line_ids:
                getattr(line, "_create_%s" % line.request_type)()
        self.action_done()
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def action_draft(self):
        self.write({"state": "draft"})
        return True
