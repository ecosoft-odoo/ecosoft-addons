# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    frappe_server_url = fields.Char(
        string="Frappe Server URL", config_parameter="odoo_etax_inet.frappe_server_url"
    )

    frappe_auth_token = fields.Char(
        string="Frappe Auth Token", config_parameter="odoo_etax_auth.frappe_auth_token"
    )
