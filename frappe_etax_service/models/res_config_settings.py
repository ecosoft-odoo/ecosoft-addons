# Copyright 2023 Ecosoft., co.th
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    frappe_server_url = fields.Char(
        config_parameter="frappe_etax_service.frappe_server_url",
    )
    frappe_auth_token = fields.Char(
        config_parameter="frappe_etax_service.frappe_auth_token",
    )
    is_send_etax_email = fields.Boolean(
        string="Send Email",
        config_parameter="frappe_etax_service.is_send_etax_email",
    )
    replacement_lock_date = fields.Integer(
        config_parameter="frappe_etax_service.replacement_lock_date",
    )

    @api.onchange("replacement_lock_date")
    def _onchange_replacement_lock_date(self):
        if self.replacement_lock_date > 30:
            self.replacement_lock_date = 1
