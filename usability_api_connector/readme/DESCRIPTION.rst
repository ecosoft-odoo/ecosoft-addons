This module provides a reusable framework for making **outbound** API calls
from Odoo to external systems.

It ships three key components:

* **common.base.api** - An abstract mixin that any Odoo model can inherit to
  gain the ability to send outbound API requests (XML-RPC or REST API),
  handle authentication, evaluate dynamic payloads, interpret responses with
  configurable result-mapping, send optional callbacks, and record every call
  in a dedicated log.
* **api.config** - A configuration model where administrators define connection
  details such as endpoint URL, API type, HTTP method, authentication
  credentials, request headers, payload templates (Python expressions),
  and response-mapping rules (success key, success value, message key).
* **api.connector.log** - A log model that stores the payload, response,
  status, calling user, and timestamp of every outbound API call for
  auditing and troubleshooting.
