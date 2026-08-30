Extends ``zort_connector`` with **Bill of Materials (BoM Kit)** support for
Zort stock synchronization.

Without this module, ``zort_connector`` pushes the raw ``qty_available`` of
each product variant. When a product is assembled from components via an MRP
BoM Kit, the sellable quantity is determined by the kit's available stock - not
the finished-good's own on-hand quantity. This module ensures Zort always
receives the correct figure.

**What it adds**

- **BoM stock sync** - a daily scheduled action
  (**Auto Update BOM Qty Available**) pushes the ``qty_available`` of every
  BoM-linked product (where **Sync with Zort** is enabled) to Zort via
  ``/Product/UpdateProductAvailableStockList``.
- **``Update Qty to Zort`` flag on BoM** - tracks whether a BoM record has
  already been synced; only unsynced BoMs are included in each run.
- **MRP operation skip** - manufacturing consumption pickings
  (``picking_type_code = mrp_operation``) are excluded from the automatic
  per-picking stock sync inherited from ``zort_connector``, preventing
  intermediate production moves from pushing incorrect stock figures.

**Dependencies**

- ``zort_connector`` (Ecosoft)
- ``mrp`` (Odoo Manufacturing)
