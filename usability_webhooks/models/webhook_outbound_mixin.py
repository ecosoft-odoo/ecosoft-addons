# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class WebhookOutboundMixin(models.AbstractModel):
    _name = "webhook.outbound.mixin"
    _description = "Outbound Webhook Mixin"

    callback_url = fields.Char(readonly=True, copy=False)

    def write(self, vals):
        if self.env.context.get("_webhook_outbound_dispatching"):
            return super().write(vals)
        candidates = self._collect_trigger_candidates(vals)
        res = super().write(vals)
        trigger_pairs = self._filter_by_domain(candidates)
        if trigger_pairs:
            self._dispatch_outbound_webhooks(trigger_pairs)
        return res

    def _collect_trigger_candidates(self, vals):
        """Before write: return [(rec, rule, domain), ...] where domain fields overlap
        vals."""
        Rule = self.env["webhook.outbound.rule"]
        rules = Rule.search([("model_name", "=", self._name), ("active", "=", True)])
        candidates = []
        for rule in rules:
            if not rule.trigger_domain:
                continue
            try:
                domain = safe_eval(rule.trigger_domain)
            except Exception:
                _logger.warning(
                    "webhook.outbound.rule '%s': invalid trigger_domain", rule.name
                )
                continue
            domain_fields = self._extract_domain_fields(domain)
            # Only relevant when at least one domain field is being written
            if not domain_fields.intersection(vals.keys()):
                continue
            for rec in self:
                candidates.append((rec, rule, domain))
        return candidates

    def _extract_domain_fields(self, domain):
        """Extract top-level field names from domain leaves."""
        fields = set()
        for item in domain:
            if isinstance(item, list | tuple) and len(item) == 3:
                # Handle dotted paths like 'partner_id.name' → 'partner_id'
                fields.add(str(item[0]).split(".")[0])
        return fields

    def _filter_by_domain(self, candidates):
        """After write: keep only (rec, rule) pairs where record now matches domain."""
        pairs = []
        for rec, rule, domain in candidates:
            try:
                if rec.filtered_domain(domain):
                    pairs.append((rec, rule))
            except Exception:
                _logger.warning(
                    "webhook.outbound.rule '%s': domain eval failed on %s(%s)",
                    rule.name,
                    rec._name,
                    rec.id,
                )
        return pairs

    def _dispatch_outbound_webhooks(self, trigger_pairs):
        Service = self.env["webhook.outbound.service"].with_context(
            _webhook_outbound_dispatching=True
        )
        for rec, rule in trigger_pairs:
            url = self._resolve_endpoint(rec, rule)
            if not url:
                _logger.warning(
                    "webhook.outbound.rule '%s': no endpoint URL for %s(%s)",
                    rule.name,
                    rec._name,
                    rec.id,
                )
                continue
            payload = self._build_payload(rec, rule)
            Service._push(url, payload, rule)

    def _resolve_endpoint(self, rec, rule):
        if rule.endpoint_source == "static":
            return rule.endpoint_url or None
        if rec.callback_url:
            return rec.callback_url
        log = self.env["api.log"].search(
            [
                ("res_model", "=", rec._name),
                ("res_id", "=", rec.id),
                ("log_type", "=", "receive"),
                ("callback_url", "!=", False),
            ],
            limit=1,
            order="id desc",
        )
        return log.callback_url or None

    def _build_payload(self, rec, rule):
        fields_spec = []
        if rule.payload_fields:
            try:
                fields_spec = json.loads(rule.payload_fields)
            except Exception:
                _logger.warning(
                    "webhook.outbound.rule '%s': invalid payload_fields JSON", rule.name
                )
        return self.env["webhook.utils"]._build_record_payload(rec, fields_spec)
