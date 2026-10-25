# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging

import requests

from odoo import api, models

from .webhook_outbound_rule import redact_url

_logger = logging.getLogger(__name__)


class WebhookOutboundService(models.AbstractModel):
    _name = "webhook.outbound.service"
    _description = "Outbound Webhook Push Service"

    @api.model
    def _push(self, rec, url, payload, rule):
        if rule.endpoint_source == "record" and not rule._is_callback_url_allowed(url):
            return self._refuse_callback_url(rec, url, rule)
        headers = {"Content-Type": "application/json"}
        if rule.auth_header:
            headers["Authorization"] = rule.auth_header

        payload_str = json.dumps(payload, ensure_ascii=False, default=str)
        state = "done"
        result_str = ""

        # A caller given callback URL was checked, not where it redirects to
        is_callback = rule.endpoint_source == "record"
        try:
            resp = requests.post(
                url,
                data=payload_str.encode(),
                headers=headers,
                timeout=10,
                allow_redirects=not is_callback,
            )
            resp.raise_for_status()
            if is_callback and resp.is_redirect:
                raise requests.HTTPError(
                    f"Redirect {resp.status_code} to {resp.headers.get('Location')} "
                    "not followed for a callback URL",
                    response=resp,
                )
            result_str = resp.text
            _logger.info(
                "Outbound webhook '%s' → %s [%s]", rule.name, url, resp.status_code
            )
        # Never block the write() that triggered the webhook
        except Exception as e:
            state = "failed"
            result_str = str(e)
            _logger.warning(
                "Outbound webhook '%s' → %s FAILED: %s",
                rule.name,
                url,
                e,
                exc_info=True,
            )

        return self._create_send_log(rec, url, rule, state, payload_str, result_str)

    @api.model
    def _refuse_callback_url(self, rec, url, rule):
        """Log, without calling it, a callback URL outside the rule's
        Allowed Callback URL."""
        # API logs are readable by internal users: never show the allowed URL
        safe_url = redact_url(url)
        message = self.env._(
            "Not sent: callback URL '%(url)s' is outside the Allowed Callback "
            "URL of rule '%(rule)s'.",
            url=safe_url,
            rule=rule.name,
        )
        _logger.warning(
            "Outbound webhook '%s': callback URL %s refused", rule.name, safe_url
        )
        return self._create_send_log(rec, safe_url, rule, "failed", "", message)

    @api.model
    def _create_send_log(self, rec, url, rule, state, payload_str, result_str):
        log = (
            self.env["api.log"]
            .sudo()
            .with_context(tracking_disable=True)
            .create(
                {
                    "model": rule.model_name,
                    "res_model": rec._name,
                    "res_id": rec.id,
                    "route": url,
                    "function_name": rule.name,
                    "log_type": "send",
                    "state": state,
                }
            )
        )
        log._save_payload(payload_str, result_str)
        return log
