# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class TierMultiValidationBinding(models.Model):
    _name = "tier.multi.validation.binding"
    _description = "Tracks auto-created multi-validation server actions per model"

    model_name = fields.Char(required=True, index=True)
    request_action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        ondelete="set null",
    )
    review_action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        ondelete="set null",
    )

    def unlink(self):
        actions = self.mapped("request_action_id") | self.mapped("review_action_id")
        res = super().unlink()
        actions.sudo().unlink()
        return res
