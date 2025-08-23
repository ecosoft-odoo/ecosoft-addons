# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    zort_connector_enabled = fields.Boolean(
        string="Enable Zort Connector",
        help="Enable the Zort Connector to connect Odoo with Zort.",
        default=False,
        config_parameter="zort_connector.enabled",
    )
    zort_endpoint_url = fields.Char(
        string="Zort Endpoint URL",
        help="The URL of the Zort endpoint to connect with.",
        default="https://open-api.zortout.com/v4",
        config_parameter="zort_connector.endpoint_url",
    )
    zort_api_key = fields.Char(
        string="Zort API Key",
        help="The API key to authenticate with the Zort endpoint.",
        default="",
        config_parameter="zort_connector.api_key",
    )
    zort_api_secret = fields.Char(
        string="Zort API Secret",
        help="The API secret to authenticate with the Zort endpoint.",
        default="",
        config_parameter="zort_connector.api_secret",
    )
    zort_store_name = fields.Char(
        help="The name of the store in Zort.",
        default="",
        config_parameter="zort_connector.store_name",
    )
    zort_warehouse_code = fields.Char(
        help="The warehouse code in Zort.",
        default="W0001",
        config_parameter="zort_connector.warehouse_code",
    )

    @api.onchange("zort_connector_enabled")
    def _onchange_zort_connector_enabled(self):
        if not self.zort_connector_enabled:
            self.env["ir.config_parameter"].sudo().set_param(
                "zort_connector.endpoint_url", ""
            )
            self.env["ir.config_parameter"].sudo().set_param(
                "zort_connector.api_key", ""
            )
            self.env["ir.config_parameter"].sudo().set_param(
                "zort_connector.api_secret", ""
            )
            self.env["ir.config_parameter"].sudo().set_param(
                "zort_connector.store_name", ""
            )
            self.env["ir.config_parameter"].sudo().set_param(
                "zort_connector.warehouse_code", ""
            )
