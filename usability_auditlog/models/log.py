# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AuditlogLog(models.Model):
    _inherit = "auditlog.log"

    ref = fields.Text()


class AuditlogLogLine(models.Model):
    _inherit = "auditlog.log.line"
    _order = "create_date desc"

    ref = fields.Text(related="log_id.ref")
