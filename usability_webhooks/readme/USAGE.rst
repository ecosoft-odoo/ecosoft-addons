Before sending a REST API request to Odoo, an initial call to authenticate the API is necessary. 
You can achieve this by calling the '/web/session/authenticate' route.

The authentication format requires a header with 'Content-type' set to 'application/json', 
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

Following successful authentication, you can proceed with two API routes:

1. '/api/create_data': This route allows the creation of new data only. 
The format for creating data should be in the following structure:

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
                  "payload": {
                     "field1": "value1",
                     ...
                  }
            }
         }
      }


2. '/api/create_update_data': This route facilitates updating data. 
If the data does not exist, it will automatically create it. 
The format follows that of 'create_data', but it requires a unique key in the field to update the values.
