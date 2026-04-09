# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class APILogTester(models.Model):
    _inherit = "api.log"

    subtype_test_id = fields.Many2one(comodel_name="mail.message.subtype")

    def action_call_api_with_params(self, a, b, note=""):
        """Test method with keyword args for call_function tests."""
        self.function_name = f"{a}-{b}-{note}"

    def action_call_api_with_context(self):
        """Test method that reads context for call_function tests."""
        is_context = self.env.context.get("is_context", "none")
        self.function_name = f"is_context={is_context}"
