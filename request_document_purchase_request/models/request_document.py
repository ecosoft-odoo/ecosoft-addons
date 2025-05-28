# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    request_type = fields.Selection(
        selection_add=[("purchase_request", "Purchase Request")],
        ondelete={"purchase_request": "cascade"},
    )
    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="request_document_id",
    )

    def _update_state_purchase_request(self, purchase_request):
        self.ensure_one()
        state_config = self.company_id.request_document_pr_state
        if state_config in ["to_approve", "approved", "done"]:
            purchase_request.button_to_approve()
            if state_config in ["approved", "done"]:
                purchase_request.button_approved()
                if state_config == "done":
                    purchase_request.button_done()
        if state_config == "rejected":
            purchase_request.button_rejected()

    def _create_purchase_request(self):
        self.ensure_one()
        purchase_request = self.purchase_request_ids.with_context(allow_edit=1)
        return self._update_state_purchase_request(purchase_request)

    def open_request_document(self):
        res = super().open_request_document()
        if self.request_type == "purchase_request":
            ctx = self.env.context.copy()
            ctx.update(
                {
                    "default_request_document_id": self.id,
                    "invisible_header": 1,
                    "create": 0,  # Not allow create
                }
            )
            if self.state == "draft":
                ctx["allow_edit"] = 1

            return {
                "type": "ir.actions.act_window",
                "views": [(False, "form")],
                "view_mode": "form",
                "res_model": "purchase.request",
                "res_id": self.purchase_request_ids.id,  # should be 1 only
                "context": ctx,
                "target": "new",
            }
        return res

    @api.depends("purchase_request_ids")
    def _compute_document(self):
        res = super()._compute_document()
        for rec in self:
            pr_id = rec.purchase_request_ids
            if pr_id:
                rec.name_document = pr_id.name
                rec.total_amount_document = pr_id.estimated_cost
        return res
