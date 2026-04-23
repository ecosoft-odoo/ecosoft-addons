**1. API Connection**

Go to **Invoicing -> Configurations -> Settings**, section **Ecosoft e-Tax Services**:

* **Frappe Server URL** - URL of the Frappe server where the e-Tax Service is installed.
* **Frappe Auth Token** - Token generated from the Frappe server.

Contact your e-Tax Service provider for these values.

**2. Document Type Code (etax.doctype.code)**

Standard INET document type codes are pre-loaded:

.. list-table::
   :header-rows: 1

   * - Code
     - Description
   * - 380
     - ใบแจ้งหนี้
   * - 388
     - ใบกำกับภาษี
   * - T01
     - ใบรับ (ใบเสร็จรับเงิน)
   * - T02
     - ใบแจ้งหนี้/ใบกำกับภาษี
   * - T03
     - ใบเสร็จรับเงิน/ใบกำกับภาษี
   * - T04
     - ใบส่งของ/ใบกำกับภาษี
   * - T05
     - ใบกำกับภาษีอย่างย่อ
   * - 80
     - ใบเพิ่มหนี้
   * - 81
     - ใบลดหนี้

Go to **Invoicing -> Configurations -> e-Tax Service -> Document Type Code** to view or add codes.

**3. e-Tax Document Type (etax.doctype)**

Map each Odoo document type to its INET document type code and report template.

Go to **Invoicing -> Configurations -> e-Tax Service -> e-Tax Doctype** and create records:

* **Form Name** - Name of the Odoo/Frappe form template (must match exactly).
* **Type** - Odoo document type: Customer Invoice, Credit Note, Debit Note, or Payment.
* **Invoice Template Source** - ``odoo`` (render PDF from Odoo) or ``frappe`` (use Frappe template).
* **Document Type Code** - Select the matching INET code (e.g. T02 for ใบแจ้งหนี้/ใบกำกับภาษี).

Example setup:

.. list-table::
   :header-rows: 1

   * - Form Name
     - Type
     - Code
   * - ใบกำกับภาษี
     - Customer Invoice
     - 388
   * - ใบแจ้งหนี้/ใบกำกับภาษี
     - Customer Invoice
     - T02
   * - ใบเพิ่มหนี้
     - Customer Debit Note
     - 80
   * - ใบลดหนี้
     - Customer Credit Note
     - 81

**4. Purpose Code (etax.purpose.code)**

Purpose codes are pre-loaded following INET convention and are linked to applicable document type codes.

Go to **Invoicing -> Configurations -> e-Tax Service -> Purpose Code** to view all codes.

Key groups:

* **TIVC** - Tax Invoice replacement (applicable to 388, T02, T03, T04, T05)
* **DBNG / DBNS** - Debit Note Goods/Services (applicable to 80)
* **CDNG / CDNS** - Credit Note Goods/Services (applicable to 81)
* **RCTC** - Receipt replacement (applicable to T01)

Purpose codes are automatically filtered by document type when creating a credit note or debit note.

**5. Replacement Lock Date**

Go to **Invoicing -> Configurations -> Settings**, section **Ecosoft e-Tax Services**:

* **Replacement Lock Date** - Day of month after which creating a replacement e-Tax document is no longer allowed (counted from the 1st of the following month). Default is ``1``.
