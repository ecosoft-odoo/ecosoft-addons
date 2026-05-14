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
| **Payload Fields** | JSON list of field names to include. Supports `field{sub1,sub2}` for relational expansion. Leave empty to send `{"id": <record_id>}` only. |
| **Authorization Header** | Optional `Authorization` header value sent with every outbound request, e.g. `Bearer <token>`. |
