# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class APILogTester(models.Model):
    _inherit = "api.log"

    subtype_test_id = fields.Many2one(comodel_name="mail.message.subtype")
