# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class WebhookOutboundService(models.AbstractModel):
    _name = "webhook.outbound.service"
    _description = "Outbound Webhook Push Service"

    @api.model
    def _push(self, rec, url, payload, rule):
        headers = {"Content-Type": "application/json"}
        if rule.auth_header:
            headers["Authorization"] = rule.auth_header

        payload_str = json.dumps(payload, ensure_ascii=False, default=str)
        state = "done"
        result_str = ""

        try:
            resp = requests.post(
                url, data=payload_str.encode(), headers=headers, timeout=10
            )
            resp.raise_for_status()
            result_str = resp.text
            _logger.info(
                "Outbound webhook '%s' → %s [%s]", rule.name, url, resp.status_code
            )
        except Exception as e:
            state = "failed"
            result_str = str(e)
            _logger.warning("Outbound webhook '%s' → %s FAILED: %s", rule.name, url, e)

        log = (
            self.env["api.log"]
            .sudo()
            .with_context(mail_notrack=True)
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
