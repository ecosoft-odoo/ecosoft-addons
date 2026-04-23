To used this module

#. Click **e-Tax Invoice** on a posted invoice or payment.
#. Select the **eTax Document Type**.
#. Enable the **Run in Background** checkbox.
#. Click **Sign**.

The document status changes to ``Processing`` immediately. The queue worker
will pick up the job and call the Frappe signing API asynchronously.
