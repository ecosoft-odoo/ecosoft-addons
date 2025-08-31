**API Logs**

Every API call can be logged under *Settings > Technical > API Configuration > API Logs*.
Each log record shows:

- **Request Preview** / **Response Preview** — first N characters of the payload (N is configurable, default 2,000)
- **Request Size** / **Response Size** — total character count of the payload
- **Full Log** button — appears when the payload exceeds the preview limit; opens the full JSON attachment

**System Parameters**

The following keys can be changed under *Settings > Technical > Parameters > System Parameters*:

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Key
     - Default
     - Description
   * - ``webhook.preview_limit``
     - ``2000``
     - Maximum characters stored in the preview fields. Payloads longer than this value are also saved as a full JSON attachment.
   * - ``webhook.create_data_log``
     - ``True``
     - Enable logging for ``/api/create_data``
   * - ``webhook.update_data_log``
     - ``True``
     - Enable logging for ``/api/update_data``
   * - ``webhook.create_update_data_log``
     - ``True``
     - Enable logging for ``/api/create_update_data``
   * - ``webhook.search_data_log``
     - ``True``
     - Enable logging for ``/api/search_data``
   * - ``webhook.call_function_log``
     - ``True``
     - Enable logging for ``/api/call_function``
   * - ``webhook.rollback_state_failed``
     - ``1``
     - Roll back the transaction when the API response is not successful
   * - ``webhook.rollback_except``
     - ``1``
     - Roll back the transaction when an unhandled exception occurs
   * - ``webhook.ignore_checkcompany_model``
     - ``[]``
     - JSON list of model names excluded from company-scoped record lookup

----

Before sending a REST API request to Odoo, an initial call to authenticate the API is necessary.
You can achieve this by calling the ``/web/session/authenticate`` route.

The authentication format requires a header with ``Content-type`` set to ``application/json``,
and the body should include:

.. code-block:: python

   {
      "jsonrpc": "2.0",
      "method": "call",
      "params": {
         "db": "<db_name>",
         "login": "<username>",
         "password": "<password>"
      }
   }

**Alternative Authentication Method (API Key)**

As an alternative to session-based authentication, you can use an **API Key** for your requests. This approach bypasses the need for an initial authentication call to ``/web/session/authenticate``.

To use this method, you must send a header with ``Authorization`` set to ``Bearer <api_key>`` for every API route call.

.. code-block:: http

   Authorization: Bearer <api_key>


**Relational Field Format**

All relational fields follow a consistent pattern based on cardinality:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Field type
     - Format
     - Example
   * - ``many2one``
     - ``{"<lookup_field>": "<value>"}``
     - ``{"name": "Customer A"}`` or ``{"id": 5}``
   * - ``many2many``
     - ``{"mode": "add"|"replace", "records": [{"<lookup_field>": "<value>"}]}``
       (``mode`` optional, defaults to ``"replace"``)
     - ``{"records": [{"name": "Tag1"}]}`` or ``{"mode": "add", "records": [...]}``
   * - ``one2many``
     - ``[{<field>: <value>, ...}, ...]``
     - ``[{"product_id": {"name": "A"}, "qty": 1}]``

The lookup field can be any indexed field on the related model (``name``, ``id``, ``ref``, etc.).
Multiple ``many2many`` items sharing the same lookup field are batched into a single DB query.


**API Routes**

Following successful authentication, you can proceed with 5 API routes:

1. ``/api/create_data``: This route allows the creation of new data only.

   .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "payload": {
                  "<field1>": "<value1>",
                  "<many2one_field_id>": {"name": "<value>"},
                  "<many2many_field_ids>": {"mode": "replace", "records": [{"name": "<val1>"}, {"name": "<val2>"}]},
                  "<one2many_field_ids>": [
                     {
                        "<field>": "<value>",
                        "<nested_m2o_id>": {"name": "<value>"}
                     }
                  ]
               },
               "auto_create": {
                  "<many2one_field_id>": {"name": "<value>", ...}
               },
               "result_field": ["<field1>", ...]  # optional: extra fields to return
            }
         }
      }

2. ``/api/create_update_data``: This route facilitates updating data.
   If the data does not exist, it will automatically create it.

   .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "search_key": {
                  "<key_field>": "<value>"
               },
               "payload": {
                  "<field1>": "<value1>",
                  "<many2one_field_id>": {"name": "<value>"},
                  "<many2many_field_ids>": {"records": [{"name": "<val1>"}]}
               },
               "result_field": ["<field1>", ...]  # optional
            }
         }
      }

3. ``/api/update_data``: This route allows updating existing data.

   .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "search_key": {
                  "<key_field>": "<value>"
               },
               "payload": {
                  "<field1>": "<value1>",
                  "<many2one_field_id>": {"id": 5},
                  "<many2many_field_ids>": {"mode": "add", "records": [{"name": "<val1>"}]}
               },
               "result_field": ["<field1>", ...]  # optional
            }
         }
      }

4. ``/api/search_data``: This route allows you to search for the value of a desired field in a model
   by using a search domain to find the desired recordset. You can also limit and order the resulting data.

   .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "payload": {
                  "search_field": ["<field1>", "<field2>", "<field3>{<subfield1>, <subfield2>}", ...],
                  "search_domain": "[('<field>', '<operator>', '<value>')]",
                  "limit": 1,
                  "order": "<field1> , <field2> desc, ..."
               }
            }
         }
      }

5. ``/api/call_function``: This route allows you to call a function on a model object based on the provided input.

   **Parameters**:
      - **name** (*str*): The name of the model to perform the function on.
      - **method** (*str*): The name of the function to call.
      - **parameter** (*dict*, optional): Keyword arguments to pass to the function.
        Use named keys so order does not matter and optional parameters can be omitted.
      - **context** (*dict*, optional): Odoo context values merged into ``env.context``
        before the method is called (e.g. ``lang``, ``force_company``, custom flags).

   .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "search_key": {
                  "<key_field>": "<value>"
               },
               "payload": {
                  "method": "<method>",
                  "parameter": {"<key>": "<value>", ...},
                  "context": {"lang": "th_TH", "<key>": "<value>", ...}
               }
            }
         }
      }

   **Example — confirm an invoice and set language context**:

   .. code-block:: python

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

**Note**:
If you want to attach a file to a record, you can add the key "attachment_ids" at any level of the payload.

   **Example Request with Attachment**:

   .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
               "search_key": {
                  "<key_field>": "value"
               },
               "payload": {
                  "attachment_ids": [
                     {
                        "name": "<file_name>",
                        "datas": "<base64_encoded_data>"
                     }
                  ],
                  ...
               }
            }
         }
      }
