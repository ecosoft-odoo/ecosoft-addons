# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class LINEApprovalWizard(models.TransientModel):
    _name = "line.approval.wizard"
    _inherit = "line.service"
    _description = "LINE Approval Wizard"

    model = fields.Many2one(
        comodel_name="ir.model",
        required=True,
    )
    template_id = fields.Many2one(
        comodel_name="line.template",
        required=True,
    )
    partner_approval = fields.Many2one(
        comodel_name="res.partner",
        required=True,
    )

    def action_approval_line(self):
        self.ensure_one()
        template = self.template_id
        model = self.env.context.get("active_model")
        res_ids = self.env.context.get("active_ids")
        line_compose = self.env["line.compose.message"].create(
            {
                "template_id": template.id,
                "attachment_ids": template.attachment_ids.ids,
                "message_type": "text",
                "partner_ids": self.partner_approval.ids,
                "model": model,
                "res_id": res_ids[0],
            }
        )
        return line_compose.send_message()
