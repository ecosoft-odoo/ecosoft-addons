# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class WebhookOutboundRule(models.Model):
    _name = "webhook.outbound.rule"
    _description = "Outbound Webhook Rule"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    model_name = fields.Char(related="model_id.model", string="Model Name", store=True)
    trigger_domain = fields.Char(
        required=True,
        help="Odoo domain evaluated after write. Webhook fires when a record "
        "transitions into matching this domain.",
    )
    endpoint_source = fields.Selection(
        selection=[
            ("static", "Static URL"),
            ("record", "Record Callback URL"),
        ],
        default="record",
        required=True,
        help="Static: always POST to endpoint_url.\n"
        "Record Callback: use callback_url stored in api.log for this record.",
    )
    endpoint_url = fields.Char(help="Used when endpoint_source is 'static'")
    payload_fields = fields.Text(
        help="JSON list of field specs. Supports field{sub1,sub2} syntax.\n"
        'Example: ["name", "state", "currency_id{id,name,code}"]\n'
        "Leave empty to send id only.",
    )
    auth_header = fields.Char(
        help="Authorization header value, e.g. 'Bearer <token>'",
    )
    note = fields.Text()
