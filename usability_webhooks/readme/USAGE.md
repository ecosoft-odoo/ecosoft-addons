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

**Alternative - API Key:** send `Authorization: Bearer <api_key>` (or the
`x-api-key: <api_key>` header) on every request. No session call needed.
Create the key in *Preferences > Account Security > API Keys* with the `rpc` scope.
When the server hosts several databases, also send `X-Odoo-Database: <db_name>`,
since there is no session to tell which one to use.

### Relational Field Format

| Field type | Format | Example |
|---|---|---|
| `many2one` | a lookup `{"<field>": "<value>", ...}` | `{"name": "Customer A"}` or `{"id": 5}` |
| `many2many` | `{"mode": "add"\|"replace", "records": [<lookup>, ...]}` (`mode` defaults to `"replace"`) | `{"records": [{"name": "Tag1"}]}` |
| `one2many` | `[{<field>: <value>, ...}, ...]` | `[{"product_id": {"name": "A"}, "qty": 1}]` |

A lookup may give several fields, like `search_key`: all must match, a list
value matches any of its items, e.g. `{"name": "VAT 7%", "type_tax_use": "sale"}`.
Each lookup must find exactly one record, for many2one and for every
`many2many` item: otherwise the call fails, telling which lookup found no
match or several (add a field, or give the `id`). `auto_create` values are
created when a lookup finds nothing. `many2many` items with one field are
searched together, in one query per field.

Lookups of fields that check the company (`check_company=True`, e.g. taxes,
journals, products or partners on most documents) use the same company scope
as Odoo: records of the payload `company_id` (a value or a lookup, e.g.
`{"name": "Company B"}`), else of the user's current company, and shared
records without company. One2many lines use the company of their parent.
A record of another company can be given by `{"id": ...}`, which is never
company scoped. This replaces the 18.0 `webhook.ignore_checkcompany_model`
parameter, which was needed because shared records were not found.

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

#### Returned fields (`result_field`)

The three routes above accept an optional `result_field` in `vals`: the fields
to read from the created or updated records, after the write. It uses the
`search_data` syntax, so relational fields can be expanded with
`field{subfield1,subfield2}`, at any depth.

```json
"result_field": ["name", "partner_id{name,vat}", "order_line{product_id{default_code},price_unit}"]
```

The values are always returned in `records`, on every route: a list with one
item per created or updated record (one for `create_data`, empty when
`update_data` matches nothing). `result` only holds the ids, and for updates
the `search_key` values sent.

```json
{
  "is_success": true,
  "result": {"id": [42], "name": "SO042"},
  "records": [
    {
      "id": 42,
      "name": "SO042",
      "partner_id": [{"id": 7, "name": "Customer A", "vat": "0105551234567"}],
      "order_line": [{"id": 90, "product_id": [{"id": 3, "default_code": "A1"}], "price_unit": 100.0}]
    }
  ]
}
```

- A plain many2one is returned as `[id, "display name"]`, an expanded one as
  a list of one dict (empty when not set), like `search_data`.
- Records and their related records are read in one query per relation, not
  per record.
- Upgrading from 18.0: `create_data` returned the values in `result`, read
  them from `records[0]` instead.
- The fields are checked before writing: an unknown field, a sub-field of a
  non relational field or unbalanced braces fail the call
  (`is_success: false`, the bad path in `messages`) and nothing is created or
  updated.

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

- `method` *(str)*: method name. Only public methods can be called, same as RPC:
  names starting with `_` and methods marked `@api.private` (e.g. `sudo`) are refused
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

When the SO is confirmed → Odoo automatically POSTs to `https://ext-system/webhook/so-status`,
provided the rule's **Allowed Callback URL** allows it (e.g. `https://ext-system/webhook`).

### Access Rights

- API logs: internal users can read them, only administrators can change them.
- Outbound webhook rules (they hold the `Authorization` header) and the
  `callback_url` of records are restricted to administrators. Webhooks still
  fire on writes made by regular users.
- A callback URL sent by an API caller is only called when it is inside the
  rule's **Allowed Callback URL** (same scheme and host, path inside its path),
  so the payload and the `Authorization` header cannot be sent to a server
  chosen by the caller, nor to internal addresses. URLs with user info,
  backslashes, whitespace or encoded `.`, `/`, `\` in the path are refused,
  and redirects answered by a callback URL are not followed (logged as
  failed). Rules migrated from 18.0 with Endpoint Source = Record Callback URL
  stop sending until this field is filled.

### Outbound Logs

All outbound calls appear in *API Logs* with **Log Type = Send**. Failed calls are marked `state = failed` with the error in the response preview.
