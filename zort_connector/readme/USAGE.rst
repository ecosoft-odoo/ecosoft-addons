Zort menu
=========

After installation a top-level **Zort** menu is available to users in the
``Zort User`` group. The menu contains:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Menu item
     - Contents
   * - Zort → Orders
     - List of all imported ``zort.order`` records
   * - Zort → Sync Logs
     - Per-page sync log with created/updated/failed counters
   * - Products → Zort Products
     - Zort ↔ Odoo product mapping table
   * - Configuration → eCommerce Channels
     - Channel settings (managers only)

Order import
============

Orders are pulled from Zort automatically every 10 minutes by the
**Auto Sync Zort Order** scheduled action.

Each Zort order is stored as a ``zort.order`` record with state **New**. A
second cron (**Process Zort Orders to Sale Orders**) converts New records into
Odoo sale orders in configurable batches (default 500).

To trigger the import manually, open **Zort → Orders** and use the
**Sync Now** action, or run the scheduled actions from
**Settings → Technical → Automation → Scheduled Actions**.

Order status mapping
====================

When a ``zort.order`` is updated by a subsequent sync run, the linked sale
order is updated automatically:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Zort status
     - Odoo action
   * - Pending
     - Sale order remains in Draft
   * - Waiting
     - Sale order is Confirmed
   * - Success
     - Delivery is validated; a draft invoice is created
   * - Voided
     - Sale order is Cancelled

Order validation
================

A third cron (**Validate Zort - Sale Orders**) checks each draft sale order
against the original Zort data:

- **Amount check** - Odoo total must match the Zort ``amount`` field.
- **Line item check** - every Zort product ID must be present in the order
  lines and the count must match.

If both checks pass, ``validate_zort_order`` is set to ``True`` and the order
is confirmed. Mismatch details are written to the **Validation Message** field
on the sale order.

To fix a missing product line manually, open the sale order and click
**Update Zort Order Lines** - the method adds any product lines present in
Zort but absent in Odoo.

Product operations
==================

Open a product variant form (**Products → Products**, switch to the variant).

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Button
     - Action
   * - Create on Zort
     - Calls ``/Product/AddProduct``; creates a ``zort.product`` mapping record
       on success. Only available when **Sync with Zort** is ticked.
   * - Update on Zort
     - Calls ``/Product/UpdateProduct`` with current name, prices, and UoM.
       Requires an existing ``zort.product`` mapping.
   * - Update Qty to Zort
     - Pushes ``qty_available`` to Zort via
       ``/Product/UpdateProductAvailableStockList``.
   * - Fetch Image from Zort
     - Downloads the product image from Zort and sets it on the Odoo product.

Stock synchronization
=====================

When a delivery or receipt picking is validated, the connector automatically
pushes the updated ``qty_available`` of each Zort-linked product to Zort
(``/Product/UpdateProductAvailableStockList``).

Pickings are **skipped** automatically if:

- The picking is an **internal transfer**.
- The picking is linked to a **Zort sale order** (stock is managed by Zort in
  that case).
- None of the move lines contain a product with a Zort mapping.

Return orders
=============

The **Auto Sync Zort Return Order** scheduled action fetches return orders from
Zort every 10 minutes (``/ReturnOrder/GetReturnOrders``):

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Zort return status
     - Odoo action
   * - Pending
     - A return picking (incoming) is created from the original delivery,
       quantities are set from the Zort return lines, and the Zort return
       number is stored on the picking.
   * - Success
     - The existing return picking is validated; a draft credit note is created
       and linked to the original sale order.

Sync logs
=========

Every order sync run creates one ``zort.sync.log`` record per page fetched.
Open **Zort → Sync Logs** to see:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Meaning
   * - Sync From / To
     - Date-time window of the sync run
   * - Page / Total Pages
     - Which page this log covers
   * - State
     - In Progress / Done / Failed
   * - Created / Updated / Failed
     - Per-page order counters
   * - Error Message
     - Details when a page fetch or upsert fails
