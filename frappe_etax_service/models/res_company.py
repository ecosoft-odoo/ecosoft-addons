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
    require_etax_email = fields.Boolean(
        string="Require Email Before Signing e-Tax",
        default=False,
        help="When Send Email is enabled, block signing if the customer has no "
        "e-Tax Email. Otherwise, sign without requesting email delivery.",
    )
    replacement_lock_date = fields.Integer(
        string="Replacement Lock Day",
        help="Day of the month after the document date until which an e-Tax "
        "replacement can be created (1-31, the last day of shorter months is "
        "used). 0 means day 1.",
    )
    is_etax_configured = fields.Boolean(
        string="Enable e-Tax",
    )

    @api.constrains("replacement_lock_date")
    def _check_replacement_lock_date(self):
        if any(not 0 <= company.replacement_lock_date <= 31 for company in self):
            raise ValidationError(
                self.env._("Replacement Lock Day must be between 0 and 31.")
            )

    @api.constrains("frappe_etax_connection_id")
    def _check_frappe_etax_connection(self):
        for company in self:
            connection = company.frappe_etax_connection_id
            if connection and connection.company_id != company:
                raise ValidationError(
                    self.env._(
                        "The Frappe e-Tax Connection must belong to the same company."
                    )
                )
