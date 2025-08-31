This module provides a standard webhook framework for Odoo with full request/response logging.

**Features**

- 5 REST API routes: ``create_data``, ``update_data``, ``create_update_data``, ``search_data``, ``call_function``
- Session-based and API Key authentication
- Automatic API log creation per request, with configurable per-route toggle
- Request and response **preview** (first N characters, configurable) stored directly on the log record
- Request and response **size** (character count) displayed on each log
- For payloads exceeding the preview limit, the full payload is stored as a JSON attachment accessible via the **Full Log** button
- Autovacuum cron to purge old logs, with optional chunk-based deletion for large datasets
