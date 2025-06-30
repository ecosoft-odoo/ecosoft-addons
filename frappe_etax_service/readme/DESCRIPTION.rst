This module integrates Odoo with the Frappe e-Tax Service (INET) to sign and retrieve certified e-Tax documents.

Key features:

* **Sign e-Tax Invoice** - Send a posted customer invoice/tax invoice to Frappe server and receive the signed PDF and XML attachments back.
* **Sign Debit Note** - Send a posted debit note (ใบเพิ่มหนี้) to Frappe server.
* **Sign Credit Note** - Send a posted credit note (ใบลดหนี้) to Frappe server, with purpose code selection.
* **Replacement e-Tax Invoice** - Create a replacement document for an already-signed invoice and re-sign with Frappe.
* **e-Tax Status Tracking** - Track signing status (Success, Processing, Error, Replaced) on each invoice.
* **Purpose Code** - Select an INET-standard purpose code when creating credit notes or debit notes.

Workflow:

#. Post a customer invoice, debit note, or credit note.
#. Click the **e-Tax Invoice** button on the document.
#. Select the e-Tax document type (e.g. ใบกำกับภาษี, ใบแจ้งหนี้/ใบกำกับภาษี) and confirm.
#. The system sends the document to Frappe server for signing.
#. Check the **e-Tax Status** on the e-Tax Info tab - when ``Success``, the signed PDF and XML are attached automatically.
#. If a signed invoice needs correction, use **Create Replacement** to create a replacement document, then sign the replacement.
