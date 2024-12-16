# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class RequestRequest(models.Model):
    _name = "request.request"
    _inherit = ["request.request", "tier.validation"]
    _state_from = ["submit"]
    _state_to = ["approve", "done"]

    _tier_validation_manual_config = False
