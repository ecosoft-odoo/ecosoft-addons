# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import re

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class WebhookOutboundMixin(models.AbstractModel):
    _name = "webhook.outbound.mixin"
    _description = "Outbound Webhook Mixin"

    callback_url = fields.Char(readonly=True, copy=False)
    webhook_last_state = fields.Selection(
        selection=[("done", "Success"), ("failed", "Failed")],
        string="Last Webhook Status",
        readonly=True,
        copy=False,
    )
    webhook_last_sent_date = fields.Datetime(
        string="Last Webhook Sent On", readonly=True, copy=False
    )

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
            log = Service._push(rec, url, payload, rule)
            rec.with_context(_webhook_outbound_dispatching=True).write(
                {
                    "webhook_last_state": log.state,
                    "webhook_last_sent_date": fields.Datetime.now(),
                }
            )

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

    def _resolve_field_value(self, rec, val):
        """If val is '{field.path}', traverse
        the dotted path on rec and return its raw value as-is. To get
        a related record's name, the path must end in an explicit
        field, e.g. '{partner_id.name}' - '{partner_id}' alone
        returns the record itself, not its display_name.
        Plain strings pass through unchanged.

        A path that crosses a multi-record one2many/many2many field
        (e.g. '{order_line.name}' with several lines) cannot be
        traversed further and would raise inside Odoo - that error is
        caught here and logged instead of propagating, so a bad
        template never blocks the triggering write().
        """
        if not isinstance(val, str):
            return val
        m = re.fullmatch(r"\{([\w.]+)\}", val.strip())
        if not m:
            return val
        try:
            obj = rec
            for part in m.group(1).split("."):
                obj = getattr(obj, part, False)
            return obj
        except Exception:
            _logger.warning(
                "webhook payload template '%s' failed to resolve on %s(%s)",
                val,
                rec._name,
                rec.id,
            )
            return None

    def _resolve_payload_value(self, rec, val):
        """Recursively resolve '{field.path}' templates inside a JSON
        object/array. Plain values (non-template strings, numbers, ...)
        pass through unchanged.
        """
        if isinstance(val, dict):
            return {k: self._resolve_dict_entry(rec, k, v) for k, v in val.items()}
        if isinstance(val, list):
            return [self._resolve_payload_value(rec, v) for v in val]
        return self._resolve_field_value(rec, val)

    def _resolve_dict_entry(self, rec, key, val):
        """A dict value that is a one-item list, where `key` names a
        one2many/many2many field on `rec`, expands into one resolved
        object per related record - using that single item as a
        per-record template. Any other value resolves normally.
        """
        field = rec._fields.get(key.strip())
        if (
            isinstance(val, list)
            and len(val) == 1
            and field is not None
            and field.type in ("one2many", "many2many")
        ):
            try:
                items = getattr(rec, key.strip())
            except Exception:
                _logger.warning(
                    "webhook payload: failed to read '%s' on %s(%s)",
                    key,
                    rec._name,
                    rec.id,
                )
                return []
            return [self._resolve_payload_value(item, val[0]) for item in items]
        return self._resolve_payload_value(rec, val)

    def _build_payload(self, rec, rule):
        if not rule.payload_fields:
            return {"id": rec.id}
        try:
            raw = json.loads(rule.payload_fields)
        except Exception:
            _logger.warning(
                "webhook.outbound.rule '%s': invalid payload_fields JSON", rule.name
            )
            return {"id": rec.id}
        if not isinstance(raw, dict):
            _logger.warning(
                "webhook.outbound.rule '%s': payload_fields must be a JSON object "
                "using '{field.path}' templates",
                rule.name,
            )
            return {"id": rec.id}
        return self._resolve_payload_value(rec, raw)
