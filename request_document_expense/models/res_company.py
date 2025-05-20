# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    request_document_ex_state = fields.Selection(
        selection=[
            ("submit", "Submitted"),
            ("approve", "Approved"),
            ("post", "Posted"),
        ],
        string="Expense State",
        default="submit",
        required=True,
        help="Default state for Expense",
    )
