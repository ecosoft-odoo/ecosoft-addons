# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    frappe_server_url = fields.Char(
        related="company_id.frappe_server_url",
        readonly=False,
    )
    frappe_auth_token = fields.Char(
        related="company_id.frappe_auth_token",
        readonly=False,
    )
    is_send_etax_email = fields.Boolean(
        string="Send Email",
        related="company_id.is_send_etax_email",
        readonly=False,
    )
    replacement_lock_date = fields.Integer(
        related="company_id.replacement_lock_date",
        readonly=False,
    )

    @api.onchange("replacement_lock_date")
    def _onchange_replacement_lock_date(self):
        if self.replacement_lock_date > 30:
            self.replacement_lock_date = 1
