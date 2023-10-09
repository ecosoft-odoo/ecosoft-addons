# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    frappe_server_url = fields.Char(
        config_parameter="frappe_etax_service.frappe_server_url",
    )

    frappe_auth_token = fields.Char(
        config_parameter="frappe_etax_service.frappe_auth_token",
    )
