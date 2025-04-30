# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    request_type = fields.Selection(
        selection_add=[("tester", "Test")],
        ondelete={"tester": "cascade"},
    )

    def _create_tester(self):
        return True
