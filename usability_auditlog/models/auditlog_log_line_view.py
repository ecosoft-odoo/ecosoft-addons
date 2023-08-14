# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AuditlogLogLineView(models.Model):
    _inherit = "auditlog.log.line.view"
    _order = "create_date desc"

    ref = fields.Text()

    def _select_query(self):
        res = super()._select_query()
        res = res + ", alog.ref"
        return res
