# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "etax.th"]
