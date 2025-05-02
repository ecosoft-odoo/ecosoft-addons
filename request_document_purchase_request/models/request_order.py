# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestOrder(models.Model):
    _inherit = "request.order"

    purchase_request_counts = fields.Integer(
        string="Purchase Request Count",
        compute="_compute_purchase_request_counts",
    )

    @api.depends("line_ids.purchase_request_ids")
    def _compute_purchase_request_counts(self):
        for rec in self:
            rec.purchase_request_counts = len(
                rec.line_ids.mapped("purchase_request_ids")
            )

    def action_open_purchase_request(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "purchase_request.purchase_request_form_action"
        )
        # Clear context
        action["context"] = []
        action["domain"] = [
            ("id", "in", self.line_ids.mapped("purchase_request_ids").ids)
        ]
        return action
