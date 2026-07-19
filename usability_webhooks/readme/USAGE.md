## Inbound (External → Odoo)

### API Logs

Every API call is logged under *Settings > Technical > API Configuration > API Logs*. Each log record shows:

- **Request Preview** / **Response Preview** - first N characters of the payload
- **Request Size** / **Response Size** - total character count
- **Full Log** button - opens the full JSON attachment when payload exceeds the preview limit
- **Callback URL** - URL stored from the inbound request for later outbound push

### Authentication

Authenticate via `/web/session/authenticate` before calling any route:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "db": "<db_name>",
    "login": "<username>",
    "password": "<password>"
  }
}
```

**Alternative - API Key:** send `Authorization: Bearer <api_key>` on every request. No session call needed.

### Relational Field Format

| Field type | Format | Example |
|---|---|---|
| `many2one` | `{"<lookup_field>": "<value>"}` | `{"name": "Customer A"}` or `{"id": 5}` |
| `many2many` | `{"mode": "add"\|"replace", "records": [...]}` (`mode` defaults to `"replace"`) | `{"records": [{"name": "Tag1"}]}` |
| `one2many` | `[{<field>: <value>, ...}, ...]` | `[{"product_id": {"name": "A"}, "qty": 1}]` |

Multiple `many2many` items sharing the same lookup field are batched into a single DB query.

### API Routes

#### 1. `/api/create_data` - create a new record

Pass optional `callback_url` to enable outbound push when the record's state changes later.

```json
{
  "params": {
    "model": "<model name>",
    "vals": {
      "callback_url": "https://your-system/webhook",
      "payload": {
        "<field1>": "<value1>",
        "<many2one_field_id>": {"name": "<value>"},
        "<many2many_field_ids>": {"mode": "replace", "records": [{"name": "<val1>"}]},
        "<one2many_field_ids>": [
          {"<field>": "<value>", "<nested_m2o_id>": {"name": "<value>"}}
        ]
      },
      "auto_create": {
        "<many2one_field_id>": {"name": "<value>"}
      },
      "result_field": ["<field1>"]
    }
  }
}
```

#### 2. `/api/create_update_data` - update if found, create if not

```json
{
  "params": {
    "model": "<model name>",
    "vals": {
      "search_key": {"<key_field>": "<value>"},
      "payload": {
        "<field1>": "<value1>",
        "<many2one_field_id>": {"name": "<value>"}
      },
      "result_field": ["<field1>"]
    }
  }
}
```

#### 3. `/api/update_data` - update an existing record

```json
{
  "params": {
    "model": "<model name>",
    "vals": {
      "search_key": {"<key_field>": "<value>"},
      "payload": {
        "<field1>": "<value1>",
        "<many2one_field_id>": {"id": 5},
        "<many2many_field_ids>": {"mode": "add", "records": [{"name": "<val1>"}]}
      },
      "result_field": ["<field1>"]
    }
  }
}
```

#### 4. `/api/search_data` - query records

Use `field{subfield1,subfield2}` to expand relational fields inline.

```json
{
  "params": {
    "model": "<model name>",
    "vals": {
      "payload": {
        "search_field": [
          "<field1>",
          "<m2o_field>{<subfield1>,<subfield2>}",
          "<o2m_field>{<subfield1>}"
        ],
        "search_domain": "[('<field>', '<operator>', '<value>')]",
        "limit": 10,
        "order": "<field1> asc, <field2> desc"
      }
    }
  }
}
```

#### 5. `/api/call_function` - call a method on a record

- `method` *(str)*: method name
- `parameter` *(dict, optional)*: keyword arguments
- `context` *(dict, optional)*: merged into `env.context` before the call

```json
{
  "params": {
    "model": "account.move",
    "vals": {
      "search_key": {"id": 26},
      "payload": {
        "method": "action_post",
        "context": {"lang": "th_TH"}
      }
    }
  }
}
```

### Attaching Files

Add `attachment_ids` at any payload level:

```json
"attachment_ids": [{"name": "<filename>", "datas": "<base64>"}]
```

---

## Outbound (Odoo → External)

When Odoo performs an action (confirm, validate, etc.), the outbound webhook automatically POSTs updated record data back to the external system - no per-model code required.

### Step 1 - Add mixin to the target model

In any private addon, add one `_inherit` line:

```python
from odoo import models

class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "webhook.outbound.mixin"]
```

All outbound behaviour is driven by rules configured in the UI.

### Step 2 - Configure an Outbound Webhook Rule

Go to *Settings > Technical > API Configuration > Outbound Webhook Rules*. See `CONFIGURE.md` for the full field reference.

**Trigger domain examples:**

```python
# Simple
[("state", "=", "sale")]

# Multiple conditions
[("state", "=", "done"), ("amount_total", ">", 100)]

# Multiple accepted values
[("state", "in", ["done", "validated"])]
```

The webhook fires only when a field in the domain is being written **and** the record matches the full domain after the write. This prevents re-triggering when unrelated fields are edited on an already-matching record.

### Payload Fields

`payload_fields` is always a JSON object. Two kinds of values are supported:

- **Static value** (string, number, bool, nested object/array) - sent as-is
- **`{field.path}` template** - resolved from the triggering record (dotted paths supported, e.g. `{partner_id.name}`), returning the raw value at the end of the path. Templates are resolved recursively, so they can appear nested inside objects/arrays at any depth. A `many2one` field must be followed by an explicit subfield (e.g. `{partner_id.name}`) - `{partner_id}` alone returns the record itself, not its name.

```json
{
  "request_code": "{name}",
  "app": "MyApp",
  "data": {"id": "{id}", "state": "{state}", "partner": "{partner_id.name}"}
}
```

Result posted to the external system:

```json
{
  "request_code": "SO001",
  "app": "MyApp",
  "data": {"id": 3, "state": "sale", "partner": "ABC Co."}
}
```

Leave `payload_fields` empty to send `{"id": <record_id>}` only.

#### Expanding one2many/many2many fields (line items)

To send a list of objects (e.g. sale order lines), use a key matching the
field name, with a **one-item array** as its value - that single item is
the per-line template, applied once for every related record:

```json
{
  "request_code": "{name}",
  "data": {
    "id": "{id}",
    "state": "{state}",
    "order_line": [
      {
        "product": "{product_id.name}",
        "qty": "{product_uom_qty}",
        "price": "{price_unit}"
      }
    ]
  }
}
```

Result posted to the external system:

```json
{
  "request_code": "SO001",
  "data": {
    "id": 3,
    "state": "sale",
    "order_line": [
      {"product": "Product A", "qty": 2.0, "price": 500.0},
      {"product": "Product B", "qty": 1.0, "price": 300.0}
    ]
  }
}
```

This only triggers when the key is an actual one2many/many2many field on
the model and the array has exactly one item - any other array is sent
as a literal value.

### Per-record Callback URL

Pass `callback_url` in the inbound `create_data` request. Odoo stores it linked to the created record. When the outbound rule fires with *Endpoint Source = Record Callback URL*, the system looks up that URL and POSTs to it.

```json
{
  "params": {
    "model": "sale.order",
    "vals": {
      "callback_url": "https://ext-system/webhook/so-status",
      "payload": {
        "partner_id": {"name": "ABC Co."},
        "order_line": [{"product_id": {"name": "Product A"}, "product_uom_qty": 1}]
      }
    }
  }
}
```

When the SO is confirmed → Odoo automatically POSTs to `https://ext-system/webhook/so-status`.

### Outbound Logs

All outbound calls appear in *API Logs* with **Log Type = Send**. Failed calls are marked `state = failed` with the error in the response preview.
