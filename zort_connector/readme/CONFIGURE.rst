1. Enable the connector
=======================

Go to **Settings → Sales → Integrations → Zort Connector** and tick
**Zort Connector**. The credential fields appear below the toggle:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - Store Name
     - Your store identifier on Zort (``storename`` request header)
   * - API Key
     - Zort API key (stored encrypted)
   * - API Secret
     - Zort API secret (stored encrypted)
   * - Warehouse Code
     - Zort warehouse code used for stock sync (default: ``W0001``)
   * - Default Tax
     - Tax applied to every order line imported from Zort

Save the settings. Disabling the toggle clears all credential fields.

2. Configure eCommerce channels
================================

Go to **Zort → Configuration → eCommerce Channels** and create one record per
sales channel that appears in the Zort ``saleschannel`` field
(e.g. ``lazada``, ``shopee``).

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - Name
     - Display name (e.g. Lazada)
   * - Code
     - Must match the Zort ``saleschannel`` value (lowercase)
   * - Platform Customer
     - Billing partner used for sale orders from this channel; falls back to
       the default marketplace customer if left empty
   * - Auto Create Customer
     - When enabled, an end-customer (``res.partner``) is created from the
       order's customer data; deduplication is done by phone or VAT number

3. Prepare products
====================

For each product that must be synchronised with Zort:

a. Set a unique **Internal Reference** (SKU / ``default_code``).
b. Open the product form and tick **Sync with Zort** (on the product variant).
c. Use the **Create on Zort** button to push the product to Zort for the first
   time. After a successful push, a **Zort Products** entry is created
   automatically with the Zort-assigned product ID (``id_zort_product``).

If a product already exists in Zort, create the mapping manually via
**Zort → Products → Zort Products** → New - fill in *Zort Product ID*, *Code*,
and link to the Odoo product.

4. Special service products
============================

Three service products are required for fee lines on imported orders. They are
created automatically on module installation:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Internal Reference
     - Purpose
   * - ``shipping_fee``
     - Shipping cost line
   * - ``zort_discount``
     - Discount line (negative amount)
   * - ``zort_voucher``
     - Voucher / coupon line

Do **not** delete or rename these products.

5. System parameters (advanced)
================================

The following ``ir.config_parameter`` keys control sync behaviour and can be
changed in **Settings → Technical → Parameters → System Parameters**:

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - Key
     - Default
     - Description
   * - ``zort_connector.order_sync_days_back``
     - ``10``
     - Days to look back when no previous sync cursor exists
   * - ``zort_connector.last_sync_datetime``
     - *(empty)*
     - Auto-updated after each successful sync run; clear to force a full re-sync
   * - ``zort_connector.pending_order_batch_size``
     - ``500``
     - Number of ``zort.order`` records processed per cron batch

6. Scheduled actions
=====================

Four scheduled actions are installed and run every **10 minutes** (all guarded
by the ``zort_connector_enabled`` company flag):

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Scheduled Action
     - What it does
   * - Auto Sync Zort Order
     - Fetches new/updated orders from Zort
   * - Process Zort Orders to Sale Orders
     - Converts pending ``zort.order`` records into Odoo sale orders
   * - Validate Zort - Sale Orders
     - Validates draft sale orders against the original Zort data
   * - Auto Sync Zort Return Order
     - Fetches return orders and creates return pickings / credit notes

The actions are created with ``noupdate="1"``; change their interval in
**Settings → Technical → Automation → Scheduled Actions**.
