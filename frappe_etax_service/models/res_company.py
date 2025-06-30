# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    frappe_server_url = fields.Char()
    frappe_auth_token = fields.Char()
    is_send_etax_email = fields.Boolean(string="Send Email")
    replacement_lock_date = fields.Integer()
