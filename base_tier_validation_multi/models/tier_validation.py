# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def action_multi_request_validation(self):
        return self._open_multi_tier_wizard("request")

    def action_multi_review(self):
        return self._open_multi_tier_wizard("review")

    def _open_multi_tier_wizard(self, validate_reject):
        names = {
            "request": self.env._("Request Validation Multiple"),
            "review": self.env._("Review Multiple"),
        }
        return {
            "name": names[validate_reject],
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "tier.validation.multi.wizard",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_ids": str(self.ids),
                "default_validate_reject": validate_reject,
            },
        }
