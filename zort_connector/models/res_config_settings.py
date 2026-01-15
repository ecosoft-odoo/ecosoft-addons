# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    zort_connector_enabled = fields.Boolean(
        help="Enable the Zort Connector to connect Odoo with Zort.",
        related="company_id.zort_connector_enabled",
        readonly=False,
    )
    zort_endpoint_url = fields.Char(
        help="The URL of the Zort endpoint to connect with.",
        related="company_id.zort_endpoint_url",
        readonly=False,
    )
    zort_api_key = fields.Char(
        help="The API key to authenticate with the Zort endpoint.",
        related="company_id.zort_api_key",
        readonly=False,
    )
    zort_api_secret = fields.Char(
        help="The API secret to authenticate with the Zort endpoint.",
        related="company_id.zort_api_secret",
        readonly=False,
    )
    zort_store_name = fields.Char(
        help="The name of the store in Zort.",
        related="company_id.zort_store_name",
        readonly=False,
    )
    zort_warehouse_code = fields.Char(
        help="The warehouse code in Zort.",
        related="company_id.zort_warehouse_code",
        readonly=False,
    )
    zort_default_tax_id = fields.Many2one(
        comodel_name="account.tax",
        help="Default tax to apply for Zort products.",
        related="company_id.zort_default_tax_id",
        readonly=False,
    )

    @api.onchange("zort_connector_enabled")
    def _onchange_zort_connector_enabled(self):
        if not self.zort_connector_enabled:
            self.company_id.zort_endpoint_url = ""
            self.company_id.zort_api_key = ""
            self.company_id.zort_api_secret = ""
            self.company_id.zort_store_name = ""
            self.company_id.zort_warehouse_code = ""
            self.company_id.zort_default_tax_id = False
