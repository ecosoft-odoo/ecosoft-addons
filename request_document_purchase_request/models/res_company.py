# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.purchase_request.models.purchase_request import _STATES


class ResCompany(models.Model):
    _inherit = "res.company"

    request_document_pr_state = fields.Selection(
        selection=_STATES,
        string="Purchase Request State",
        default="to_approve",
        required=True,
        help="Default state for Purchase Request",
    )
