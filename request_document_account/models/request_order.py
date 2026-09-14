# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import UserError


class RequestOrder(models.Model):
    _inherit = "request.order"

    vendor_bill_count = fields.Integer(compute="_compute_vendor_bill_count")

    def unlink(self):
        if self.line_ids.move_ids:
            raise UserError(
                self.env._(
                    "Delete or unlink Vendor Bills before deleting their request."
                )
            )
        return super().unlink()

    def write(self, vals):
        if "company_id" in vals:
            for rec in self:
                if rec.line_ids.move_ids and vals["company_id"] != rec.company_id.id:
                    raise UserError(
                        self.env._(
                            "Unlink Vendor Bills before changing the request company."
                        )
                    )
        return super().write(vals)

    @api.depends("line_ids.move_ids")
    def _compute_vendor_bill_count(self):
        for rec in self:
            rec.vendor_bill_count = len(rec.line_ids.move_ids)

    def action_submit(self):
        self.line_ids._check_vendor_bill()
        return super().action_submit()

    def action_process_document(self):
        for rec in self.filtered(lambda order: order.line_ids.move_ids):
            if rec.state != "approve":
                raise UserError(
                    self.env._("Approve the request before processing Vendor Bills.")
                )
        res = super().action_process_document()
        for rec in self:
            if rec.company_id.request_document_bill_state == "posted":
                rec.line_ids.move_ids.action_post()
        return res

    def action_open_vendor_bills(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_in_invoice_type"
        )
        action["domain"] = [("id", "in", self.line_ids.move_ids.ids)]
        return action
