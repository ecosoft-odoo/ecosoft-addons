# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ChannelPartner(models.Model):
    _inherit = "mail.channel.partner"

    use_line = fields.Boolean(string="Use LINE", default=False)
