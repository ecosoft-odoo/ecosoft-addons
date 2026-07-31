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
        help="JSON object. Static values are sent as-is; '{field.path}' "
        "templates are resolved from the record, recursively at any nesting "
        "level.\nA one2many/many2many field can be expanded into a list of "
        "objects: give a key matching the field name a one-item array as "
        'value, e.g. "order_line": [{"product": "{product_id.name}"}].\n'
        "'{field.path:format}' converts the value, where format is one of:\n"
        "- label: selection value -> its translated label\n"
        "- join: comma separated values, for a path crossing a x2many field\n"
        "- date: datetime -> date part only\n"
        "- text: html -> plain text\n"
        "'{@_webhook_method}' or '{@_webhook_method(arg1, arg2)}' calls a "
        "method of the record and sends what it returns; only methods named "
        "'_webhook_*' can be called and arguments are passed as strings.\n"
        'Example: {"request_code": "{name}", '
        '"data": {"id": "{id}", "state": "{state:label}"}}\n'
        "Leave empty to send id only.",
    )
    auth_header = fields.Char(
        help="Authorization header value, e.g. 'Bearer <token>'",
    )
    note = fields.Text()
