# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import re
from collections import defaultdict

from odoo import fields, models
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

PATH_RE = re.compile(r"\{([\w.]+)\}")
FORMAT_RE = re.compile(r"\{([\w.]+):(\w+)\}")
CALL_RE = re.compile(r"\{@(_webhook_\w+)(?:\((.*)\))?\}")


class WebhookOutboundMixin(models.AbstractModel):
    _name = "webhook.outbound.mixin"
    _description = "Outbound Webhook Mixin"

    # Admin only: whoever sets it receives the payload and the rule's
    # Authorization header
    callback_url = fields.Char(readonly=True, copy=False, groups="base.group_system")
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
        """Before write: return [(records, rule, domain), ...] for the rules
        whose domain fields overlap vals."""
        Rule = self.env["webhook.outbound.rule"].sudo()
        specs = [
            (rule_id, domain)
            for rule_id, domain, domain_fields in Rule._get_trigger_specs(self._name)
            # Only relevant when at least one domain field is being written
            if domain_fields.intersection(vals)
        ]
        # Rules share their prefetch, their fields are read at once
        rules = Rule.browse(rule_id for rule_id, _domain in specs)
        return [
            (self, rule, domain)
            for rule, (_rule_id, domain) in zip(rules, specs, strict=True)
        ]

    def _filter_by_domain(self, candidates):
        """After write: keep only (rec, rule) pairs where record now matches domain."""
        pairs = []
        for records, rule, domain in candidates:
            try:
                matched = records.filtered_domain(domain)
            except Exception:
                _logger.warning(
                    "webhook.outbound.rule '%s': domain eval failed on %s%s",
                    rule.name,
                    records._name,
                    records.ids,
                    exc_info=True,
                )
                continue
            pairs.extend((rec, rule) for rec in matched)
        return pairs

    def _dispatch_outbound_webhooks(self, trigger_pairs):
        Service = self.env["webhook.outbound.service"].with_context(
            _webhook_outbound_dispatching=True
        )
        callback_urls = self._get_callback_urls(
            self.browse(
                {
                    rec.id
                    for rec, rule in trigger_pairs
                    if rule.endpoint_source == "record"
                }
            )
        )
        last_states = {}
        for rec, rule in trigger_pairs:
            if rule.endpoint_source == "static":
                url = rule.endpoint_url
            else:
                url = callback_urls.get(rec.id)
            if not url:
                _logger.warning(
                    "webhook.outbound.rule '%s': no endpoint URL for %s(%s)",
                    rule.name,
                    rec._name,
                    rec.id,
                )
                continue
            if rule.endpoint_source == "record" and not rule._is_callback_url_allowed(
                url
            ):
                log = Service._refuse_callback_url(rec, url, rule)
            else:
                payload = self._build_payload(rec, rule)
                log = Service._push(rec, url, payload, rule)
            last_states[rec.id] = log.state
        # One write per state, the last rule sent wins
        ids_by_state = defaultdict(list)
        for rec_id, state in last_states.items():
            ids_by_state[state].append(rec_id)
        now = fields.Datetime.now()
        for state, rec_ids in ids_by_state.items():
            self.browse(rec_ids).with_context(_webhook_outbound_dispatching=True).write(
                {"webhook_last_state": state, "webhook_last_sent_date": now}
            )

    def _get_callback_urls(self, records):
        """{record id: callback URL}: the record's callback_url, or else the one
        of its latest received API log. Logs are searched once for all records."""
        urls = {rec.id: rec.callback_url for rec in records.sudo() if rec.callback_url}
        missing = [rec_id for rec_id in records.ids if rec_id not in urls]
        if missing:
            Log = self.env["api.log"].sudo()
            latest = Log._read_group(
                [
                    ("res_model", "=", records._name),
                    ("res_id", "in", missing),
                    ("log_type", "=", "receive"),
                    ("callback_url", "!=", False),
                ],
                ["res_id"],
                ["id:max"],
            )
            for log in Log.browse(log_id for _res_id, log_id in latest):
                urls[log.res_id] = log.callback_url
        return urls

    def _resolve_field_value(self, rec, val):
        """Resolve one payload template. Three forms are supported, any
        other string passes through unchanged:

        '{field.path}'
            Traverse the dotted path on rec and return its raw value as-is.
            To get a related record's name, the path must end in an explicit
            field, e.g. '{partner_id.name}' - '{partner_id}' alone returns
            the record itself, not its display_name. A path crossing a
            multi-record one2many/many2many cannot be traversed further, use
            the ':join' format for that.

        '{field.path:format}'
            Same traversal, then a conversion. See _format_payload_values
            for the available formats.

        '{@_webhook_method}' / '{@_webhook_method(arg1, arg2)}'
            Call a method of rec and send what it returns. Only methods
            named '_webhook_*' can be called, arguments are passed as
            plain strings.

        Anything raised while resolving is logged and turned into None, so a
        bad template never blocks the triggering write().
        """
        if not isinstance(val, str):
            return val
        val = val.strip()
        call = CALL_RE.fullmatch(val)
        if call:
            return self._resolve_method_value(rec, call.group(1), call.group(2))
        fmt_match = FORMAT_RE.fullmatch(val)
        path_match = PATH_RE.fullmatch(val)
        if not fmt_match and not path_match:
            return val
        try:
            if fmt_match:
                return self._resolve_formatted_value(
                    rec, fmt_match.group(1), fmt_match.group(2)
                )
            obj = rec
            for part in path_match.group(1).split("."):
                obj = getattr(obj, part, False)
            return obj
        except Exception:
            _logger.warning(
                "webhook payload template '%s' failed to resolve on %s(%s)",
                val,
                rec._name,
                rec.id,
                exc_info=True,
            )
            return None

    def _resolve_method_value(self, rec, method_name, raw_args):
        args = [arg.strip() for arg in raw_args.split(",")] if raw_args else []
        method = getattr(rec, method_name, None)
        if not callable(method):
            _logger.warning(
                "webhook payload: '%s' is not a method of %s", method_name, rec._name
            )
            return None
        try:
            return method(*args)
        except Exception:
            _logger.warning(
                "webhook payload method '%s' failed on %s(%s)",
                method_name,
                rec._name,
                rec.id,
                exc_info=True,
            )
            return None

    def _resolve_formatted_value(self, rec, path, fmt):
        """Traverse `path` with mapped() - so it can cross a x2many field -
        then convert the collected values with `fmt`.
        """
        parts = path.split(".")
        records = rec
        for part in parts[:-1]:
            records = records.mapped(part)
        field = records._fields[parts[-1]]
        # Unset values are False, except for booleans; keep 0
        values = [
            val
            for val in records.mapped(parts[-1])
            if val or (val == 0 and val is not False) or field.type == "boolean"
        ]
        values = self._format_payload_values(field, values, fmt)
        if fmt == "join" or len(values) > 1:
            return ", ".join(str(val) for val in values)
        return values[0] if values else ""

    def _format_payload_values(self, field, values, fmt):
        """label: selection value -> its translated label
        join:  keep every value, comma separated
        date:  datetime -> date part only
        text:  html -> plain text
        """
        if fmt == "label":
            labels = dict(field._description_selection(self.env))
            return [labels.get(val, val) for val in values]
        if fmt == "date":
            return [fields.Date.to_string(fields.Date.to_date(val)) for val in values]
        if fmt == "text":
            return [html2plaintext(val) for val in values]
        return values

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
                    exc_info=True,
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
                "webhook.outbound.rule '%s': invalid payload_fields JSON",
                rule.name,
                exc_info=True,
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
