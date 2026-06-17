This module provides a standard webhook framework for Odoo with full
request/response logging and config-driven outbound push notifications.

**Inbound (External → Odoo)**

* 5 REST API routes: ``create_data``, ``update_data``, ``create_update_data``,
  ``search_data``, ``call_function``
* Session-based and API Key authentication
* Friendly relational field format: ``many2one``, ``many2many``, ``one2many``
  resolved by name or id
* ``auto_create`` support for missing related records
* Automatic API log creation per request, with configurable per-route toggle
* Request and response **preview** (first N characters, configurable) stored on
  the log record
* Request and response **size** (character count) displayed on each log
* Full payload stored as JSON attachment (accessible via **Full Log** button)
  when preview limit exceeded
* Autovacuum cron to purge old logs, with optional chunk-based deletion

**Outbound (Odoo → External)**

* ``webhook.outbound.rule`` - config-driven rules: which model + domain → which
  endpoint
* ``webhook.outbound.mixin`` - add to any model with a single ``_inherit`` line;
  no per-model code required
* **Trigger domain**: full Odoo domain expression evaluated after ``write()``;
  webhook fires only when a record transitions into matching the domain
* **Endpoint source**: static URL per rule, or per-record ``callback_url`` passed
  by the external system at create time
* **Payload fields**: JSON list supporting ``field{sub1,sub2}`` expansion for
  relational fields - same syntax as ``search_data``
* Outbound calls logged in API Logs (``log_type = send``) with success/failed
  state
