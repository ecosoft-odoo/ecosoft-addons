# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    request_document_bill_state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")],
        string="Vendor Bill State",
        default="draft",
        required=True,
        help="State of Vendor Bills when their request is processed.",
    )
