# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    frappe_etax_connection_id = fields.Many2one(
        comodel_name="frappe.etax.connection",
        string="Frappe e-Tax Connection",
        check_company=True,
        ondelete="restrict",
    )
    is_send_etax_email = fields.Boolean(string="Send Email")
    replacement_lock_date = fields.Integer()
    is_etax_configured = fields.Boolean(
        string="Enable e-Tax",
    )

    @api.constrains("frappe_etax_connection_id", "is_etax_configured")
    def _check_frappe_etax_connection(self):
        for company in self:
            connection = company.frappe_etax_connection_id
            if company.is_etax_configured and not connection:
                raise ValidationError(
                    self.env._(
                        "Select a Frappe e-Tax Connection before enabling e-Tax."
                    )
                )
            if connection and connection.company_id != company:
                raise ValidationError(
                    self.env._(
                        "The Frappe e-Tax Connection must belong to the same company."
                    )
                )
