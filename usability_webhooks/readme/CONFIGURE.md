## System Parameters

Go to *Settings > Technical > Parameters > System Parameters* to adjust the following keys:

| Key | Default | Description |
|-----|---------|-------------|
| `webhook.preview_limit` | `2000` | Maximum characters stored in the preview fields. Payloads longer than this are also saved as a full JSON attachment. |
| `webhook.create_data_log` | `True` | Enable logging for `/api/create_data` |
| `webhook.update_data_log` | `True` | Enable logging for `/api/update_data` |
| `webhook.create_update_data_log` | `True` | Enable logging for `/api/create_update_data` |
| `webhook.search_data_log` | `True` | Enable logging for `/api/search_data` |
| `webhook.call_function_log` | `True` | Enable logging for `/api/call_function` |
| `webhook.rollback_state_failed` | `1` | Roll back the transaction when the API response is not successful |
| `webhook.rollback_except` | `1` | Roll back the transaction when an unhandled exception occurs |
| `webhook.ignore_checkcompany_model` | `[]` | JSON list of model names excluded from company-scoped record lookup |

## Outbound Webhook Rules

Go to *Settings > Technical > API Configuration > Outbound Webhook Rules* to configure outbound push rules.

| Field | Description |
|-------|-------------|
| **Model** | The Odoo model to watch (e.g. `sale.order`) |
| **Trigger Domain** | Odoo domain evaluated after `write()`. Webhook fires when a record transitions into matching the domain. Uses the domain widget - select a model first to get field suggestions. |
| **Endpoint Source** | `Static URL` - always POST to the configured URL. `Record Callback URL` - use the `callback_url` stored from the inbound request. |
| **Endpoint URL** | Required when Endpoint Source is `Static URL`. |
| **Payload Fields** | A JSON object. Static values are sent as-is; `{field.path}` templates are resolved from the record (dotted paths supported, e.g. `{partner_id.name}`), recursively at any nesting level. A one2many/many2many field can be expanded into a list of objects: give the key matching the field name a one-item array as value, e.g. `"order_line": [{"product": "{product_id.name}"}]`. Leave empty to send `{"id": <record_id>}` only. |
| **Authorization Header** | Optional `Authorization` header value sent with every outbound request, e.g. `Bearer <token>`. |

### Payload templates

| Template | Result |
|----------|--------|
| `{field.path}` | The raw value. A path crossing a multi-record one2many/many2many cannot be traversed - use `:join` instead. |
| `{field.path:label}` | Selection value replaced by its translated label, e.g. `sale` -> `Sales Order`. |
| `{field.path:join}` | Every value along the path, comma separated. Traverses x2many fields, e.g. `{order_line.product_id.name:join}`. |
| `{field.path:date}` | Date part only of a datetime field, e.g. `2026-07-31`. |
| `{field.path:text}` | Html field converted to plain text. |
| `{@_webhook_method}` | Calls `_webhook_method()` on the record and sends what it returns. |
| `{@_webhook_method(arg1, arg2)}` | Same, with arguments passed as plain strings. |

Only methods named `_webhook_*` can be called. Define them on the model that
inherits `webhook.outbound.mixin`, for example to look up a value in another
model. Anything that fails to resolve is logged and sent as `null`, so a bad
template never blocks the `write()` that triggered the webhook.
