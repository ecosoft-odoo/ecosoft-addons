# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    frappe_etax_connection_id = fields.Many2one(
        related="company_id.frappe_etax_connection_id",
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
    is_etax_configured = fields.Boolean(
        related="company_id.is_etax_configured",
        readonly=False,
    )

    @api.onchange("replacement_lock_date")
    def _onchange_replacement_lock_date(self):
        if self.replacement_lock_date > 30:
            self.replacement_lock_date = 1
