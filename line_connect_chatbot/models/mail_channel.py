# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailChannel(models.Model):
    _inherit = "mail.channel"

    line_connect = fields.Boolean(string="Connect to LINE", default=False)
