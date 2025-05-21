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

    def _get_state_progression_paths(self):
        return {
            "to_approve": ["button_to_approve"],
            "approved": ["button_to_approve", "button_approved"],
            "in_progress": [
                "button_to_approve",
                "button_approved",
                "button_in_progress",
            ],
            "done": ["button_to_approve", "button_approved", "button_done"],
            "rejected": ["button_rejected"],
        }

    def _update_state_purchase_request(self, purchase_request):
        self.ensure_one()
        purchase_request = purchase_request.with_context(allow_edit=1)
        state_config = self.company_id.request_document_pr_state
        state_progression_paths = self._get_state_progression_paths()
        for method_name in state_progression_paths.get(state_config, []):
            method_process = getattr(purchase_request, method_name, None)
            if method_process:
                method_process()

    def _create_purchase_request(self):
        self.ensure_one()
        return self._update_state_purchase_request(self.purchase_request_ids)

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
