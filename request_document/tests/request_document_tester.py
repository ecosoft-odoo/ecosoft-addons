# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class RequestDocument(models.Model):
    _inherit = "request.document"

    @api.model
    def _get_request_type_selection(self):
        return super()._get_request_type_selection() + [("tester", "Test")]

    def _create_tester(self):
        return True
