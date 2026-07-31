# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class APILogOutboundTester(models.Model):
    _name = "api.log"
    _inherit = ["api.log", "webhook.outbound.mixin"]

    def _webhook_echo(self, *args):
        return "|".join(args) if args else self.function_name

    def _webhook_boom(self):
        raise ValueError("boom")
