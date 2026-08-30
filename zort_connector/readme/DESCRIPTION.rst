Connects Odoo with `Zort <https://www.zortout.com/>`_ (Thai multi-channel
e-commerce platform) for bidirectional synchronization of orders, products,
inventory, and returns.

**Zort API endpoints used**

.. list-table::
   :header-rows: 1
   :widths: 5 40 55

   * - #
     - Endpoint
     - Purpose
   * - 1
     - ``/Order/GetOrders``
     - Pull orders from Zort into Odoo
   * - 2
     - ``/ReturnOrder/GetReturnOrders``
     - Pull return orders from Zort
   * - 3
     - ``/Product/AddProduct``
     - Create a new product in Zort
   * - 4
     - ``/Product/UpdateProduct``
     - Push product name/price changes to Zort
   * - 5
     - ``/Product/UpdateProductAvailableStockList``
     - Push available-stock quantity to Zort

**Key features**

- **Automatic order import** - scheduled every 10 minutes; supports paginated
  results and a configurable look-back window (default 10 days).
- **Status-driven workflow** - Zort status changes trigger matching Odoo actions:

  - *Pending* → Sale Order stays draft
  - *Waiting* → Sale Order confirmed
  - *Success* → delivery validated + draft invoice created
  - *Voided* → Sale Order cancelled

- **Product & stock push** - create/update products in Zort from the product
  form; stock is pushed automatically on every non-Zort, non-internal picking
  validation.
- **Return order processing** - Zort return orders are fetched every 10 minutes;
  a return picking is created on *Pending* status and validated (with a draft
  credit note) on *Success* status.
- **Multi-channel support** - eCommerce channel records map Zort
  ``saleschannel`` codes (Lazada, Shopee, Tiktok, …) to Odoo billing partners
  and control auto-customer-creation.
- **Robust sync logging** - every sync run is recorded in **Zort > Sync Logs**
  with per-page created/updated/failed counters and error messages.
- **Extensible hooks** - key methods (``_dispatch_sync_page``,
  ``_dispatch_pending_orders_batch``, ``hook_process_sku``) are designed to be
  overridden by add-on modules (e.g. an async queue-job extension).
