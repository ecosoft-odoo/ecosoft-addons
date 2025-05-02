# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class RequestOrder(models.Model):
    _name = "request.order"
    _inherit = ["request.order", "tier.validation"]
    _state_from = ["submit"]
    _state_to = ["approve", "done"]

    _tier_validation_manual_config = False
