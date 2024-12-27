# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LINEComposer(models.TransientModel):
    _name = "line.compose.message"
    _inherit = ["base.line.process", "mail.thread"]
    _description = "LINE composition wizard"

    # content
    message = fields.Text()
    # template_id = fields.Many2one(
    #     'mail.template', 'Use template', index=True,
    #     domain="[('model', '=', model)]")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "line_compose_message_ir_attachments_rel",
        "wizard_id",
        "attachment_id",
        "Attachments",
    )

    # destination
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="line_compose_message_res_partner_rel",
        column1="wizard_id",
        column2="partner_id",
        string="LINE to",
        domain="[('line_access_token', '!=', False)]",
    )

    model = fields.Char("Related Document Model", index=True)
    res_id = fields.Integer("Related Document ID", index=True)

    def action_send_line(self):
        self.ensure_one()
        if self.model and self.res_id:
            original_record = self.env[self.model].browse(self.res_id)
            original_record.message_post(
                body=self.message,
                message_type="line",
                line_partner_ids=self.partner_ids.ids,
            )
        return
