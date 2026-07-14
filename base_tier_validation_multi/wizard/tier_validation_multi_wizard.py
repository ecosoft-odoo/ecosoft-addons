# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import api, fields, models
from odoo.exceptions import UserError


class TierValidationMultiWizard(models.TransientModel):
    _name = "tier.validation.multi.wizard"
    _description = "Tier Validation Multi Wizard"

    res_model = fields.Char(required=True)
    res_ids = fields.Char(help="JSON list of record IDs to validate/reject")
    comment = fields.Char()
    validate_reject = fields.Selection(
        selection=[
            ("request", "Request Validation"),
            ("review", "Review"),
            ("validate", "Validate"),
            ("reject", "Reject"),
        ],
        required=True,
        default="review",
    )
    record_count = fields.Integer(compute="_compute_record_count")
    has_comment = fields.Boolean(compute="_compute_has_comment")

    @api.depends("res_ids", "res_model", "validate_reject")
    def _compute_has_comment(self):
        for wiz in self:
            if wiz.validate_reject == "request" or not wiz.res_ids or not wiz.res_model:
                wiz.has_comment = False
                continue
            ids = json.loads(wiz.res_ids or "[]")
            records = (
                self.env[wiz.res_model].browse(ids).filtered(lambda r: r.can_review)
            )
            found = False
            for rec in records:
                sequences = rec._get_sequences_to_approve(self.env.user)
                if wiz.validate_reject == "validate":
                    reviews = rec.review_ids.filtered(
                        lambda x, sequences=sequences: (
                            x.sequence in sequences or x.approve_sequence_bypass
                        )
                        and x.definition_id.allow_multi_validate
                    )
                else:
                    reviews = rec.review_ids.filtered(
                        lambda x, sequences=sequences: x.sequence in sequences
                        and x.definition_id.allow_multi_validate
                    )
                if True in reviews.mapped("definition_id.has_comment"):
                    found = True
                    break
            wiz.has_comment = found

    @api.depends("res_ids")
    def _compute_record_count(self):
        for wiz in self:
            ids = json.loads(wiz.res_ids or "[]")
            wiz.record_count = len(ids)

    def action_confirm(self):
        """Entry point for Request Validation."""
        return self._do_confirm()

    def action_validate(self):
        self.validate_reject = "validate"
        return self._do_confirm()

    def action_reject(self):
        self.validate_reject = "reject"
        return self._do_confirm()

    def _do_confirm(self):
        self.ensure_one()
        ids = json.loads(self.res_ids or "[]")
        if not ids:
            raise UserError(self.env._("No records selected."))

        if self.validate_reject == "request":
            records = (
                self.env[self.res_model]
                .browse(ids)
                .filtered(lambda r: r.need_validation)
            )
            if not records:
                raise UserError(
                    self.env._("No selected records need a validation request.")
                )
            records.request_validation()
            return

        records = self.env[self.res_model].browse(ids).filtered(lambda r: r.can_review)
        if not records:
            raise UserError(
                self.env._("None of the selected records can be reviewed by you.")
            )
        for rec in records:
            sequences = rec._get_sequences_to_approve(self.env.user)
            if self.validate_reject == "validate":
                reviews = rec.review_ids.filtered(
                    lambda x, sequences=sequences: (
                        x.sequence in sequences or x.approve_sequence_bypass
                    )
                    and x.definition_id.allow_multi_validate
                )
                if self.comment:
                    reviews.write({"comment": self.comment})
                rec._validate_tier(reviews)
            else:
                reviews = rec.review_ids.filtered(
                    lambda x, sequences=sequences: x.sequence in sequences
                    and x.definition_id.allow_multi_validate
                )
                if self.comment:
                    reviews.write({"comment": self.comment})
                rec._rejected_tier(reviews)
            rec._update_counter({"review_deleted": True})
