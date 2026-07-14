# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    allow_multi_validate = fields.Boolean(
        string="Allow Multi Validation",
        help="When enabled, automatically adds Validate/Reject Selected actions "
        "to this model's list view.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        models_to_sync = {v.get("model") for v in vals_list if v.get("model")}
        for model_name in models_to_sync:
            self._sync_multi_actions_for_model(model_name)
        return records

    def write(self, vals):
        old_models = set(self.mapped("model")) if "model" in vals else set()
        res = super().write(vals)
        if "allow_multi_validate" in vals or "model" in vals:
            new_models = set(self.mapped("model"))
            for model_name in old_models | new_models:
                self._sync_multi_actions_for_model(model_name)
        return res

    def unlink(self):
        models_to_sync = set(self.mapped("model"))
        res = super().unlink()
        for model_name in models_to_sync:
            self._sync_multi_actions_for_model(model_name)
        return res

    @api.model
    def _sync_multi_actions_for_model(self, model_name):
        if not model_name:
            return
        has_multi = bool(
            self.search(
                [("model", "=", model_name), ("allow_multi_validate", "=", True)],
                limit=1,
            )
        )
        binding = self.env["tier.multi.validation.binding"].search(
            [("model_name", "=", model_name)], limit=1
        )
        if has_multi and not binding:
            self._create_multi_binding(model_name)
        elif not has_multi and binding:
            binding.unlink()

    @api.model
    def _create_multi_binding(self, model_name):
        ir_model = self.env["ir.model"].search([("model", "=", model_name)], limit=1)
        if not ir_model:
            return

        def _make_action(name, code):
            return (
                self.env["ir.actions.server"]
                .sudo()
                .create(
                    {
                        "name": name,
                        "model_id": ir_model.id,
                        "binding_model_id": ir_model.id,
                        "binding_view_types": "list",
                        "state": "code",
                        "code": code,
                    }
                )
            )

        request_action = _make_action(
            "Request Validation",
            "action = records.action_multi_request_validation()",
        )
        review_action = _make_action(
            "Review Selected",
            "action = records.action_multi_review()",
        )
        self.env["tier.multi.validation.binding"].create(
            {
                "model_name": model_name,
                "request_action_id": request_action.id,
                "review_action_id": review_action.id,
            }
        )
