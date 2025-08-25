# Copyright 2025 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ApiConfig(models.Model):
    _name = "api.config"
    _inherit = "common.base.api"  # For test api
    _description = "API Configuration"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    api_type = fields.Selection(
        selection=[
            ("xmlrpc", "XML-RPC"),
            ("rest_api", "Rest API"),
        ],
        string="API Type",
        required=True,
    )
    description = fields.Char()
    model_id = fields.Many2one(
        comodel_name="ir.model",
        ondelete="cascade",
    )
    endpoint_system = fields.Selection(
        selection=[("odoo", "Odoo"), ("external", "External REST")],
    )
    endpoint_url = fields.Char(string="Endpoint URL")
    callback_url = fields.Char(string="Callback URL")
    disable_ssl = fields.Boolean(
        string="Disable SSL Verification",
        help="Disable SSL verification for API calls",
    )
    route_path = fields.Char()
    method = fields.Selection(
        selection=[
            ("get", "GET"),
            ("post", "POST"),
            ("put", "PUT"),
            ("delete", "DELETE"),
        ]
    )
    active = fields.Boolean(default=True)
    auth_required = fields.Boolean()
    auth_username = fields.Char(string="Username")
    auth_password = fields.Char(string="Password")
    auth_db = fields.Char(string="Database")
    auth_token = fields.Char()

    # XML-RPC
    execute_model = fields.Char()
    execute_method = fields.Char()
    execute_context = fields.Char(default='{"context": {}}')

    # Rest API
    headers = fields.Text()

    # Python code
    python_code = fields.Text(
        help="Write Python code that the action will execute. Some variables are "
        "available for use; help about python expression is given in the help tab."
    )
    params_code = fields.Text(
        string="Params",
        help="Python expression returning a dict of URL query parameters (?key=value). "
        "Evaluated with the same context as JSON / Payload (rec, env). "
        "For GET/DELETE these are merged with the payload params. "
        "For POST/PUT these are sent alongside the request body.",
    )
    save_log = fields.Boolean()

    # Result mapping - configurable per external system
    result_success_key = fields.Char(
        string="Success Key",
        default="is_success",
        help="Dot-notation path to the success indicator in the API response.\n"
        "Examples:\n"
        "  'is_success'         - {'is_success': True}\n"
        "  'result.is_success'  - {'result': {'is_success': True}}\n"
        "  '0.status'           - [{'status': 'ok', ...}]\n"
        "Leave empty to treat any non-empty response as success.",
    )
    result_success_value = fields.Char(
        string="Success Value",
        help="Expected value that means success (compared as string).\n"
        "Examples: 'True', 'success', '200', 'ok'\n"
        "Leave empty to use truthy check on the key value.",
    )
    result_message_key = fields.Char(
        string="Message Key",
        default="message",
        help="Dot-notation path to the error/info message in the API response.\n"
        "Examples:\n"
        "  'message'              - {'message': 'error detail'}\n"
        "  'error.message.value'  - {'error': {'message': {'value': '...'}}}\n"
        "  'errors.0'             - {'errors': ['first error', ...]}",
    )

    def action_test_call_api(self):
        return self.action_call_api(self.code)
