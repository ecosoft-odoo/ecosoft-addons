# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    zort_connector_enabled = fields.Boolean(
        related="company_id.zort_connector_enabled",
        readonly=False,
        help="Enable the Zort Connector to connect Odoo with Zort.",
    )
    zort_api_key = fields.Char(
        related="company_id.zort_api_key",
        readonly=False,
        help="The API key to authenticate with the Zort endpoint.",
    )
    zort_api_secret = fields.Char(
        related="company_id.zort_api_secret",
        readonly=False,
        help="The API secret to authenticate with the Zort endpoint.",
    )
    zort_store_name = fields.Char(
        related="company_id.zort_store_name",
        readonly=False,
        help="The name of the store in Zort.",
    )
    zort_warehouse_code = fields.Char(
        related="company_id.zort_warehouse_code",
        readonly=False,
        help="The warehouse code in Zort.",
    )
    zort_default_tax_id = fields.Many2one(
        comodel_name="account.tax",
        related="company_id.zort_default_tax_id",
        readonly=False,
        help="Default tax to apply for Zort products.",
    )

    @api.onchange("zort_connector_enabled")
    def _onchange_zort_connector_enabled(self):
        if not self.zort_connector_enabled:
            self.company_id.zort_api_key = ""
            self.company_id.zort_api_secret = ""
            self.company_id.zort_store_name = ""
            self.company_id.zort_warehouse_code = ""
            self.company_id.zort_default_tax_id = False
