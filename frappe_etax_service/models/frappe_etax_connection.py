# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from urllib.parse import urlparse

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FrappeEtaxConnection(models.Model):
    _name = "frappe.etax.connection"
    _description = "Frappe e-Tax Connection"
    _order = "company_id, name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete="cascade",
    )
    server_url = fields.Char(
        string="Frappe Server URL",
        required=True,
        help="Base URL of the Frappe e-Tax server, without an API route.",
    )
    auth_token = fields.Char(
        string="Frappe Auth Token",
        required=True,
        copy=False,
        help="Authentication token in [api_key]:[api_secret] format.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "frappe_etax_connection_name_company_uniq",
            "unique(name, company_id)",
            "A Frappe e-Tax connection with this name already exists for the company.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("server_url"):
                vals["server_url"] = self._normalize_server_url(vals["server_url"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("server_url"):
            vals["server_url"] = self._normalize_server_url(vals["server_url"])
        return super().write(vals)

    @api.model
    def _normalize_server_url(self, server_url):
        return server_url.strip().rstrip("/")

    @api.constrains("server_url")
    def _check_server_url(self):
        for connection in self:
            parsed = urlparse(connection.server_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValidationError(
                    self.env._("Frappe Server URL must be a valid HTTP or HTTPS URL.")
                )

    @api.constrains("auth_token")
    def _check_auth_token(self):
        for connection in self:
            api_key, separator, api_secret = connection.auth_token.partition(":")
            if not separator or not api_key.strip() or not api_secret.strip():
                raise ValidationError(
                    self.env._(
                        "Frappe Auth Token must use [api_key]:[api_secret] format."
                    )
                )
