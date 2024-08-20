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

Following successful authentication, you can proceed with five API routes:

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

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
                  "<unique key>": "value",  # can be ID or name search string
                  "field1": "value1",
                  ...
            }
         }
      }


3. '/api/update_data': This route allows updating exist data.
 using a unique key in the field to find the desired data and update values in that recordset.

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
                  "payload": {
                     "<unique key>": "value", # can be ID or name search string
                     "field1": "value1",
                     ...
                  }
            }
         }
      }


4. '/api/search_data': This route allows you to search for the value of a desired field in a model.
 by using a search domain to find the desired recordset. You can also limit and order the resulting data

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
                  "payload": {
                     "search_field": ["field1", "field2", ...],
                     "search_domain": "[('field', 'operator', 'value')]",
                     "limit": 1,
                     "order": "field1 , field2 desc, ...",
                  }
            }
         }
      }


  5. '/api/call_function': This route allows you to call a function on a model object based on the provided input.
      Parameters:
        - name (str): The name of the model to perform the function on.
        - method (str): The name of the function to call.
        - parameter (dict):
            A dictionary containing the arguments to pass to the function. (if any)

  .. code-block:: python

      {
         "params": {
            "model": "<model name>",
            "vals": {
                  "payload": {
                     "name": "<name>",
                     "method": "<method>",
                     "parameter": {},
                  }
            }
         }
      }
