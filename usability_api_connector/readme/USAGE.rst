To use this method:

1. Go to menu **Settings > Technical > Web Services > API Exports**.
2. Create a new record and fill in the following fields:

   * **API Name / Code** - A human-readable name and a unique code used to
     look up the configuration programmatically (e.g. ``action_call_api('MY_CODE')``).
   * **Model** - The Odoo model this configuration is related to (optional, informational).
   * **Endpoint System** - Choose ``Odoo`` to connect to another Odoo instance, or ``External`` for a generic REST service.
   * **Endpoint URL** - The base URL of the remote system (e.g. ``https://other-odoo.example.com``).
   * **Route Path** - The path appended to the endpoint URL. For XML-RPC the
     default is ``/xmlrpc/2/object``; for REST it is the specific route (e.g. ``/api/v1/products``).
   * **Callback URL** - An optional URL that receives a POST callback after a successful API call.
   * **API Type**:

     - ``XML-RPC`` - Calls ``execute_kw`` on a remote Odoo instance. Requires
       **Execute Model**, **Execute Method**, and **Execute Context**.
     - ``REST API`` - Sends an HTTP request. Requires **HTTP Method**
       (GET / POST / PUT / DELETE) and optional **Headers** (a Python dict
       expression, e.g. ``{"Authorization": f"Bearer {auth_token}"}``).

   * **Authentication** - Enable **Auth Required** and provide **Database**,
     **Username**, and **Password**. The module handles login automatically:
     for XML-RPC it obtains a ``uid``, for REST API it obtains a
     ``session_id`` cookie. The token is cached on the configuration record
     and refreshed on expiry.
   * **Disable SSL** - Skips SSL certificate verification (development only).
   * **Save Log** - When enabled, every call creates an ``api.connector.log``
     record regardless of success or failure.

3. Configure the **JSON / Payload** tab with a Python expression that
   evaluates to a ``dict`` or ``list``. Available variables:

   * ``rec`` - the current record calling the API
   * ``env`` - the Odoo environment
   * ``today`` - ``fields.Date.context_today(self)``
   * ``today_datetime`` - ``fields.Datetime.context_timestamp(self, now())``

   Example::

      {"name": rec.name, "ref": rec.ref, "amount": rec.amount_total}

4. For REST API, optionally configure the **Params** tab with a Python
   expression returning a ``dict`` of URL query parameters
   (e.g. ``{"page": 1, "lang": "th"}``).

5. Configure **Result Mapping** to tell the module how to interpret the
   remote response:

   * **Success Key** - Dot-notation path to the success indicator
     (default ``is_success``). Examples: ``result.is_success``, ``0.status``.
   * **Success Value** - Expected string value that means success
     (e.g. ``True``, ``ok``, ``200``). Leave empty for a truthy check.
   * **Message Key** - Dot-notation path to the error message
     (default ``message``). Example: ``error.message.value``.

Click the **Test API** button on the configuration form to execute a test
call. The result (or error) is displayed in the **Test Result** tab.

To add outbound API capability to your own model:

1. Inherit the ``common.base.api`` mixin::

      class MyModel(models.Model):
          _name = "my.model"
          _inherit = ["my.model", "common.base.api"]

2. Call the API by code::

      self.action_call_api("MY_API_CODE")

3. Override ``_hook_update_data`` to process the response::

      def _hook_update_data(self, code_api, result):
          if code_api == "MY_API_CODE":
              # REST: result is the parsed JSON dict
              # XML-RPC: result is {"is_success": True, "result": <raw>}
              self.write({"external_id": result.get("id")})

   The mixin automatically handles authentication, request execution,
   error handling, status updates (``api_status``), and log creation.

Viewing Logs
~~~~~~~~~~~~

Navigate to **Settings > Technical > Web Services > Outbound API Logs** to
review all outgoing API call history. Each log entry records:

* API code and name
* Endpoint system
* Source model and record ID
* Status (Success / Failed / Draft)
* Payload sent and response received
* Error message (if any)
* User who triggered the call and timestamp
