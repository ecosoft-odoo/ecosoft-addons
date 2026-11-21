# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, tools


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

    @tools.ormcache("name")
    def _test_lookup_category_ids(self, name):
        """Stand-in for core ormcaches (e.g. xmlid lookup) in dry_run tests."""
        Category = self.env["res.partner.category"]
        return tuple(Category.search([("name", "=", name)]).ids)

    def action_create_cached_category(self, name):
        """Create a tag (no cache invalidation) and put its id in an ormcache."""
        self.env["res.partner.category"].create({"name": name})
        return self._test_lookup_category_ids(name)

    def action_add_hooks(self):
        """Register hooks like bus (postcommit data) or rollback cleanups."""
        cr = self.env.cr
        cr.postcommit.add(lambda: None)
        cr.postcommit.data.setdefault("webhook.test", []).append(self.id)
        cr.prerollback.add(self._test_on_rollback)
        cr.postrollback.add(self._test_on_rollback)
        return True

    def _test_on_rollback(self):
        """Patched in tests."""
