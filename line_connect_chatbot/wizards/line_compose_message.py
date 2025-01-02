# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


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
        required=True,
    )

    model = fields.Char("Related Document Model", index=True)
    res_id = fields.Integer("Related Document ID", index=True)

    def action_send_line(self):
        self.ensure_one()
        if self.model and self.res_id:
            original_record = self.env[self.model].browse(self.res_id)
            message_list = []
            # TODO: Support flex message and else
            if self.message:
                message_list.append(
                    {
                        "type": "text",
                        "text": self.message,
                    }
                )
            attachments = self.attachment_ids
            if attachments:
                attachments.generate_access_token()
                for attach in attachments:
                    content_url = "{}/web/image/{}?access_token={}".format(
                        self.env["ir.config_parameter"]
                        .sudo()
                        .get_param("web.base.url"),
                        attach.id,
                        attach.access_token,
                    )
                    if attach.index_content == "image":
                        message_list.append(
                            {
                                "type": "image",
                                "originalContentUrl": content_url,
                                "previewImageUrl": content_url,
                            }
                        )
                    # Send data with template file
                    elif attach.mimetype == "application/pdf":
                        # TODO: support only pdf, other file can't open
                        message_list.append(
                            {
                                "type": "template",
                                "altText": attach.name,
                                "template": {
                                    "type": "buttons",
                                    "title": attach.name,
                                    "text": attach.mimetype[:59],  # limit 60 char
                                    "actions": [
                                        {
                                            "type": "uri",
                                            "label": "Open file",
                                            "uri": content_url,
                                        }
                                    ],
                                },
                            }
                        )
                    else:
                        raise UserError(
                            _("Only PDF and Image files are allowed as attachments.")
                        )
            original_record.message_post(
                body=message_list,
                message_type="line",
                line_partner_ids=self.partner_ids.ids,
                attachment_ids=self.attachment_ids.ids,
            )
        return
