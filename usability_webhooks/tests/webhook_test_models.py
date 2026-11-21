# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class WebhookTestRecord(models.Model):
    _name = "webhook.test.record"
    _inherit = ("webhook.outbound.mixin",)
    _description = "Webhook Test Record"

    name = fields.Char()
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done"), ("failed", "Failed")],
        default="draft",
    )
    amount = fields.Integer()
    company_id = fields.Many2one(comodel_name="res.company")
    partner_id = fields.Many2one(comodel_name="res.partner", check_company=True)
    note = fields.Html()
    tag_id = fields.Many2one(comodel_name="res.partner.category")
    tag_ids = fields.Many2many(comodel_name="res.partner.category")
    reference = fields.Reference(selection=[("res.partner.category", "Tag")])
    line_ids = fields.One2many(
        comodel_name="webhook.test.line", inverse_name="record_id"
    )
    # Like account.move
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        domain=[("res_model", "=", "webhook.test.record")],
    )

    def action_with_params(self, a, b, note=""):
        """Public method with keyword arguments, for call_function tests"""
        self.name = f"{a}-{b}-{note}"

    def action_with_context(self):
        """Public method reading the context, for call_function tests"""
        self.name = f"is_context={self.env.context.get('is_context', 'none')}"

    def action_done(self):
        """Public method writing a trigger field, for dry run tests"""
        self.state = "done"
        return True

    def action_create_cached_tag(self, name, raw_sql=False, fail=False):
        """Create a tag and put its id in an ormcache, for dry run tests"""
        if raw_sql:
            self.env.cr.execute(
                SQL(
                    "INSERT INTO res_partner_category (name, active) VALUES (%s, TRUE)",
                    json.dumps({"en_US": name}),
                )
            )
        else:
            self.env["res.partner.category"].create({"name": name})
        tag_ids = self._test_tag_ids(name)
        if fail:
            raise UserError(name)
        return tag_ids

    def action_add_hooks(self):
        """Register hooks like bus (postcommit data) or Gelato (rollback)"""
        cr = self.env.cr
        cr.postcommit.add(lambda: None)
        cr.postcommit.data.setdefault("webhook.test", []).append(self.id)
        cr.prerollback.add(self._test_on_rollback)
        cr.postrollback.add(self._test_on_rollback)
        return True

    def _test_on_rollback(self):
        """Patched in tests"""

    @api.ormcache("name")
    def _test_tag_ids(self, name):
        """Stand-in for core ormcaches (e.g. xmlid lookup) in dry run tests"""
        return tuple(self.env["res.partner.category"].search([("name", "=", name)]).ids)

    def _webhook_echo(self, *args):
        return "|".join(args) if args else self.name

    def _webhook_boom(self):
        raise ValueError("boom")


class WebhookTestLine(models.Model):
    _name = "webhook.test.line"
    _description = "Webhook Test Line"

    record_id = fields.Many2one(
        comodel_name="webhook.test.record", required=True, ondelete="cascade"
    )
    name = fields.Char()
    tag_id = fields.Many2one(comodel_name="res.partner.category")
    partner_id = fields.Many2one(comodel_name="res.partner", check_company=True)
