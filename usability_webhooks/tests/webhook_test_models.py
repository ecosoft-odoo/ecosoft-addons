# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
