# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import posixpath
import re
from urllib.parse import unquote

import requests
from urllib3.util import parse_url

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)
DEFAULT_PORTS = {"http": 80, "https": 443}
# Backslashes, whitespace and control characters are parsed differently by
# URL parsers and servers
UNSAFE_URL_RE = re.compile(r"[\\\x00-\x20\x7f]")
# After one decoding, an encoded '.', '/' or '\' left in the path could
# still be read as '..' or a separator by a receiver decoding twice
UNSAFE_PATH_RE = re.compile(r"\\|%2e|%2f|%5c", re.IGNORECASE)


def _url_origin_path(url):
    """Return ((scheme, host, port), normalized path) of an http(s) URL,
    or None when it is not one.

    The URL is parsed the way ``requests`` sends it: urllib.parse reads e.g.
    'https://evil.com\\@allowed.com' as host 'allowed.com', while requests
    connects to 'evil.com'.
    """
    if not url or UNSAFE_URL_RE.search(url):
        return None
    try:
        parsed = parse_url(requests.Request("POST", url).prepare().url)
    except (requests.RequestException, ValueError):  # missing scheme, bad port
        return None
    scheme = (parsed.scheme or "").lower()
    if scheme not in DEFAULT_PORTS or not parsed.host or parsed.auth:
        return None
    port = parsed.port or DEFAULT_PORTS[scheme]
    # Decode and resolve '..' so a path cannot leave the allowed prefix
    path = unquote(parsed.path or "/")
    if UNSAFE_PATH_RE.search(path):
        return None
    return (scheme, parsed.host.lower(), port), posixpath.normpath(path)


def redact_url(url):
    """``url`` without userinfo, query, fragment nor control characters, to
    be logged and shown to users."""
    try:
        parsed = parse_url(url or "")
    except ValueError:
        parsed = None
    if parsed and parsed.scheme and parsed.host:
        port = f":{parsed.port}" if parsed.port else ""
        url = f"{parsed.scheme}://{parsed.host}{port}{parsed.path or ''}"
    return re.sub(r"[\x00-\x1f\x7f]", "", url or "")[:500]


class WebhookOutboundRule(models.Model):
    _name = "webhook.outbound.rule"
    _description = "Outbound Webhook Rule"
    # Changing rules clears the cache of _get_trigger_specs
    _clear_cache_name = "default"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    model_name = fields.Char(
        related="model_id.model", string="Model Name", store=True, index=True
    )
    trigger_domain = fields.Char(
        required=True,
        help="Odoo domain evaluated after write. Webhook fires when a record "
        "transitions into matching this domain.",
    )
    endpoint_source = fields.Selection(
        selection=[
            ("static", "Static URL"),
            ("record", "Record Callback URL"),
        ],
        default="record",
        required=True,
        help="Static: always POST to endpoint_url.\n"
        "Record Callback: use callback_url stored in api.log for this record, "
        "only when it is inside the Allowed Callback URL.",
    )
    endpoint_url = fields.Char(help="Used when endpoint_source is 'static'")
    allowed_callback_url = fields.Char(
        string="Allowed Callback URL",
        help="Required when endpoint_source is 'record'. A callback URL given "
        "by the caller is only called when it has the same scheme and host "
        "(port included) and its path is inside this path, e.g. "
        "'https://partner.example.com/webhook' allows "
        "'https://partner.example.com/webhook/so/12'. Other URLs are not "
        "called and logged as failed, so the payload and the Authorization "
        "header are never sent to a host chosen by the caller.",
    )
    payload_fields = fields.Text(
        help="JSON object. Static values are sent as-is; '{field.path}' "
        "templates are resolved from the record, recursively at any nesting "
        "level.\nA one2many/many2many field can be expanded into a list of "
        "objects: give a key matching the field name a one-item array as "
        'value, e.g. "order_line": [{"product": "{product_id.name}"}].\n'
        "'{field.path:format}' converts the value, where format is one of:\n"
        "- label: selection value -> its translated label\n"
        "- join: comma separated values, for a path crossing a x2many field\n"
        "- date: datetime -> date part only\n"
        "- text: html -> plain text\n"
        "'{@_webhook_method}' or '{@_webhook_method(arg1, arg2)}' calls a "
        "method of the record and sends what it returns; only methods named "
        "'_webhook_*' can be called and arguments are passed as strings.\n"
        'Example: {"request_code": "{name}", '
        '"data": {"id": "{id}", "state": "{state:label}"}}\n'
        "Leave empty to send id only.",
    )
    auth_header = fields.Char(
        help="Authorization header value, e.g. 'Bearer <token>'",
    )
    note = fields.Text()

    @api.constrains("endpoint_source", "allowed_callback_url")
    def _check_allowed_callback_url(self):
        for rule in self.filtered(lambda r: r.endpoint_source == "record"):
            if not _url_origin_path(rule.allowed_callback_url):
                raise ValidationError(
                    self.env._(
                        "Rule '%s': Allowed Callback URL must be an http(s) URL, "
                        "e.g. https://partner.example.com/webhook",
                        rule.name,
                    )
                )

    def _is_callback_url_allowed(self, url):
        """Whether the caller given ``url`` may be called for this rule: same
        scheme, host and port as the Allowed Callback URL, path inside its path.
        """
        self.ensure_one()
        allowed = _url_origin_path(self.allowed_callback_url)
        target = _url_origin_path(url)
        if not allowed or not target or allowed[0] != target[0]:
            return False
        prefix = allowed[1].rstrip("/")
        path = target[1]
        return not prefix or path == prefix or path.startswith(f"{prefix}/")

    @api.model
    @api.ormcache("model_name")
    def _get_trigger_specs(self, model_name):
        """Return ``((rule_id, domain, domain_fields), ...)`` of the active
        rules of ``model_name``. Cached: it is called on every write() of the
        models using ``webhook.outbound.mixin``."""
        specs = []
        rules = self.sudo().search(
            [("model_name", "=", model_name), ("active", "=", True)]
        )
        for rule in rules:
            # An invalid rule is skipped, it must never block the write()
            try:
                domain = Domain(safe_eval(rule.trigger_domain))
            except Exception:
                _logger.warning(
                    "webhook.outbound.rule '%s': invalid trigger_domain",
                    rule.name,
                    exc_info=True,
                )
                continue
            # Top-level field of each condition, e.g. 'partner_id.name' -> 'partner_id'
            domain_fields = frozenset(
                cond.field_expr.split(".")[0] for cond in domain.iter_conditions()
            )
            specs.append((rule.id, domain, domain_fields))
        return tuple(specs)
