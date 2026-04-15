# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import os
import re
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

ZORT_GET_ORDER = "zort_get_order"

# ---------------------------------------------------------------------------
# Demo mode - load JSON fixtures instead of calling the live API.
# Set to True while testing to avoid consuming real API tokens.
# ---------------------------------------------------------------------------
_DEMO_MODE = False
_DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "demo")


class ZortOrder(models.Model):
    _name = "zort.order"
    _inherit = ["mail.thread", "mail.activity.mixin", "common.base.api"]
    _description = "Zort Order"
    _rec_name = "zort_order_number"
    _order = "zort_order_date desc, id desc"

    zort_order_id = fields.Char(
        string="Zort Order ID",
        index=True,
        readonly=True,
    )
    zort_order_number = fields.Char(
        string="Order Number",
        index=True,
        readonly=True,
    )
    zort_status = fields.Char(readonly=True)
    zort_order_date = fields.Datetime(string="Order Date", readonly=True)
    zort_update_date = fields.Datetime(string="Updated on Zort", readonly=True)
    total_amount = fields.Float(readonly=True)
    payment_amount = fields.Float(readonly=True)
    shipping_cost = fields.Float(readonly=True)
    source_channel = fields.Char(readonly=True)
    channel_order_id = fields.Char(readonly=True)
    customer_name = fields.Char(readonly=True)
    customer_phone = fields.Char(readonly=True)
    customer_address = fields.Text(readonly=True)
    remark = fields.Text(readonly=True)
    raw_data = fields.Text(string="Raw Data (JSON)", readonly=True)
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("processed", "Processed"),
            ("error", "Error"),
        ],
        default="new",
    )
    sale_order_ids = fields.One2many(
        comodel_name="sale.order",
        inverse_name="zort_order_id",
        readonly=True,
    )
    sync_log_id = fields.Many2one(
        comodel_name="zort.sync.log",
        string="Sync Log",
        readonly=True,
    )

    _sql_constraints = [
        (
            "zort_order_id_unique",
            "UNIQUE(zort_order_id)",
            "Zort Order ID must be unique.",
        )
    ]

    @api.model
    def _get_zort_api_config(self):
        """Return the active api.config record with code=ZORT_MAIN."""
        return (
            self.env["api.config"]
            .sudo()
            .search([("code", "=", ZORT_GET_ORDER), ("active", "=", True)], limit=1)
        )

    @api.model
    def _get_last_sync(self):
        ICP = self.env["ir.config_parameter"].sudo()
        last_sync = ICP.get_param("zort_connector.last_sync_datetime", "")
        days_back = int(ICP.get_param("zort_connector.order_sync_days_back", 10))
        if last_sync:
            sync_dt = fields.Datetime.to_datetime(last_sync)
            return fields.Date.to_string(sync_dt.date())
        from_date = fields.Date.today() - timedelta(days=days_back)
        return fields.Date.to_string(from_date)

    @staticmethod
    def _parse_zort_datetime(value):
        """Parse Zort datetime string (ISO 8601 'T' or Odoo space separator)."""
        if not value:
            return False
        return fields.Datetime.to_datetime(str(value).replace("T", " "))

    @api.model
    def _prepare_order_vals(self, order_data, sync_log):
        """Map a Zort API order dict to zort.order field values."""
        return {
            "zort_order_id": str(order_data.get("id", "")),
            "zort_order_number": order_data.get("number", ""),
            "zort_status": order_data.get("status", ""),
            "zort_order_date": self._parse_zort_datetime(order_data.get("orderdate")),
            "zort_update_date": self._parse_zort_datetime(
                order_data.get("updatedatetime")
            ),
            "total_amount": order_data.get("amount") or 0.0,
            "payment_amount": order_data.get("paymentamount") or 0.0,
            "shipping_cost": order_data.get("shippingamount") or 0.0,
            "source_channel": order_data.get("saleschannel", ""),
            "channel_order_id": order_data.get("integrationShop", ""),
            "customer_name": order_data.get("customername", ""),
            "customer_phone": order_data.get("customerphone", ""),
            "customer_address": order_data.get("customeraddress", ""),
            "remark": order_data.get("description", ""),
            "raw_data": json.dumps(order_data, ensure_ascii=False),
            "sync_log_id": sync_log.id,
        }

    @api.model
    def _upsert_order(self, order_data, sync_log):
        """Create or update a zort.order record from raw API data"""
        zort_order_id = str(order_data.get("id", ""))
        if not zort_order_id:
            return None, "skipped"

        vals = self._prepare_order_vals(order_data, sync_log)
        existing = self.search([("zort_order_id", "=", zort_order_id)], limit=1)
        if existing:
            existing.write(vals)
            self._post_upsert_order(existing)
            return existing, "updated"

        return self.create(vals), "created"

    def action_create_sale_order(self):
        zort_orders = self.filtered(
            lambda zo: zo.state == "new" and not zo.sale_order_ids
        )
        if not zort_orders:
            return

        product_cache, channel_cache = zort_orders._build_so_caches()
        so_vals_list = []
        valid_zorts = self.env["zort.order"]
        for zort in zort_orders:
            try:
                vals = zort._prepare_dict_so(
                    product_cache=product_cache, channel_cache=channel_cache
                )
                so_vals_list.append(vals)
                valid_zorts |= zort
            except Exception as e:
                _logger.error(
                    "Error preparing SO for zort.order %s: %s", zort.zort_order_id, e
                )
                zort.write({"state": "error"})
        if not so_vals_list:
            return

        sale_orders = self.env["sale.order"].create(so_vals_list)
        valid_zorts.write({"state": "processed"})
        return sale_orders

    @api.model
    def _get_pending_order_batch_size(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return int(ICP.get_param("zort_connector.pending_order_batch_size", 500))

    def _build_so_caches(self):
        """Build product and channel lookup caches for a recordset batch"""
        channel_codes = [(c or "").lower() for c in self.mapped("source_channel") if c]
        channel_recs = self.env["zort.ecommerce.channel"].search(
            [("code", "in", channel_codes)]
        )
        channel_cache = {rec.code: rec for rec in channel_recs}

        special_skus = ["shipping_fee", "zort_discount", "zort_voucher"]
        products = self.env["product.product"].search(
            [("default_code", "in", special_skus)]
        )
        product_cache = {p.default_code: p for p in products}
        return product_cache, channel_cache

    def _prepare_dict_so(self, product_cache=None, channel_cache=None):
        """Return a sale.order vals dict for this zort.order (no DB write)."""
        self.ensure_one()
        zort_order = json.loads(self.raw_data or "{}")
        partner_id, zort_customer_id = self._get_customers_data(
            zort_order, channel_cache=channel_cache
        )
        order_lines = self._prepare_sale_order_lines(
            zort_order, product_cache=product_cache
        )
        return {
            "partner_id": partner_id,
            "zort_order_id": self.id,
            "zort_order_number": self.zort_order_number,
            "zort_order_status": self.zort_status,
            "zort_payment_status": zort_order.get("paymentstatus"),
            "zort_sales_channel": self.source_channel,
            "zort_customer_id": zort_customer_id,
            "order_line": order_lines,
        }

    def _get_customers_data(self, zort_order, channel_cache=None):
        """
        Determine the billing partner (marketplace) and the platform-specific
        customer (end customer) based on the sales channel.
        Returns: tuple (partner_id, zort_customer_id)
        """
        sales_channel = (self.source_channel or "").lower()
        if channel_cache is not None:
            ecommerce_channel = channel_cache.get(
                sales_channel, self.env["zort.ecommerce.channel"]
            )
        else:
            ecommerce_channel = self.env["zort.ecommerce.channel"].search(
                [("code", "=", sales_channel)], limit=1
            )

        # 1. Marketplace Customer (Billing Partner)
        default_customer = self.env.ref("zort_connector.marketplace_customer_1")
        partner_id = ecommerce_channel.partner_id.id or default_customer.id

        # 2. Platform Customer (End Customer)
        zort_customer_id = False
        if ecommerce_channel and ecommerce_channel.auto_create_customer:
            customer = self._create_customer(zort_order)
            if customer:
                zort_customer_id = customer.id

        return partner_id, zort_customer_id

    def _create_customer(self, zort_order):
        """Find or create a res.partner from this order's customer data."""
        vals = {
            "name": zort_order.get("customername", "Online Customer"),
            "phone": zort_order.get("customerphone", ""),
            "email": zort_order.get("customeremail", ""),
            "street": zort_order.get("customeraddress", ""),
            "city": zort_order.get("customerprovince", ""),
            "zip": zort_order.get("customerpostcode", ""),
            "vat": zort_order.get("customeridnumber", ""),
            "is_company": False,
        }
        if vals["phone"]:
            phone = self._validate_customer_phone(vals["phone"])
            existing = self.env["res.partner"].search([("phone", "=", phone)], limit=1)
            if existing:
                return existing
        if vals["vat"]:
            existing = self.env["res.partner"].search(
                [("vat", "=", vals["vat"])], limit=1
            )
            if existing:
                return existing
        return self.env["res.partner"].create(vals)

    @staticmethod
    def _validate_customer_phone(phone: str) -> str:
        """Return the last 9 digits of the phone number."""
        phone = phone.strip()
        # keep only digits
        phone = re.sub(r"\D", "", phone)

        # case: 660812345678
        if phone.startswith("660"):
            phone = "0" + phone[3:]

        # case: 66812345678
        elif phone.startswith("66"):
            phone = "0" + phone[2:]

        return phone

    def hook_process_sku(self, sku):
        """
        Hook to process SKU before fetching product.
        Override in custom modules to modify SKU format if needed.
        Example: Remove suffix after '#' (e.g., 'a-1234#left' -> 'a-1234').
        """
        return sku

    def _get_product_by_sku(self, sku):
        """Fetch Odoo product.product by Zort product ID (SKU)."""
        product_id = self.hook_process_sku(sku)
        zort_product = self.env["zort.product"].search(
            [("id_zort_product", "=", product_id)], limit=1
        )
        if zort_product and zort_product.product_id:
            return zort_product.product_id
        return self.env["product.product"]

    def _prepare_sale_order_lines(self, zort_order, product_cache=None):
        """Build sale.order line command tuples from this order's raw_data."""
        order_lines = []
        for line in zort_order.get("list", []):
            product = self._get_product_by_sku(line.get("productid"))
            if not product:
                _logger.warning(
                    "Product with SKU %s not found. Skipping line.", line.get("sku")
                )
                continue
            order_lines.append(
                Command.create(
                    {
                        "product_id": product.id,
                        "product_uom_qty": line.get("number", 1),
                        "price_unit": line.get("pricepernumber", 0.0),
                        "name": product.name,
                        "tax_id": [
                            Command.set(self.env.company.zort_default_tax_id.ids)
                        ],
                    },
                )
            )
        shipping_amount = zort_order.get("shippingamount", 0.0)
        if shipping_amount > 0:
            order_lines.append(
                self._prepare_shipping_line(
                    shipping_amount, product_cache=product_cache
                )
            )
        discount = zort_order.get("discount", 0.0)
        if discount:
            order_lines.append(
                self._prepare_discount_line(
                    float(discount), product_cache=product_cache
                )
            )
        voucher_amount = zort_order.get("voucheramount", 0.0)
        if voucher_amount > 0:
            order_lines.append(
                self._prepare_voucher_line(voucher_amount, product_cache=product_cache)
            )
        return order_lines

    def _prepare_shipping_line(self, shipping_amount, product_cache=None):
        """Return a sale.order line command tuple for shipping fee."""
        if product_cache is not None:
            product = product_cache.get("shipping_fee", self.env["product.product"])
        else:
            product = self.env["product.product"].search(
                [("default_code", "=", "shipping_fee")], limit=1
            )
        return Command.create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "price_unit": shipping_amount,
                "name": "Shipping Fee",
            }
        )

    def _prepare_discount_line(self, discount, product_cache=None):
        """Return a sale.order line command tuple for discount (negative price)."""
        if product_cache is not None:
            product = product_cache.get("zort_discount", self.env["product.product"])
        else:
            product = self.env["product.product"].search(
                [("default_code", "=", "zort_discount")], limit=1
            )
        return Command.create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "price_unit": -float(discount),
                "name": "Discount",
            }
        )

    def _prepare_voucher_line(self, voucher_amount, product_cache=None):
        """Return a sale.order line command tuple for voucher."""
        if product_cache is not None:
            product = product_cache.get("zort_voucher", self.env["product.product"])
        else:
            product = self.env["product.product"].search(
                [("default_code", "=", "zort_voucher")], limit=1
            )
        return Command.create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "price_unit": voucher_amount,
                "name": "Voucher",
            }
        )

    def _post_upsert_order(self, zort_order):
        """
        Hook called after an existing zort.order is updated.
        If a sale.order is already linked, sync the updated status back.
        Override in submodules to add custom behaviour.
        """
        active_so = zort_order.sale_order_ids.filtered(lambda so: so.state != "cancel")[
            :1
        ]
        if active_so:
            active_so._update_sale_order_from_zort(zort_order)

    @api.model
    def action_process_pending_orders(self):
        """Entry point for cron: dispatch pending zort.order records in batches.

        Splits pending records into configurable-size batches and dispatches each
        via ``_dispatch_pending_orders_batch``.  Override that method in
        ``zort_connector_queue`` to switch to asynchronous queue-job execution.
        """
        pending = self.search([("state", "=", "new"), ("sale_order_ids", "=", False)])
        if not pending:
            return

        batch_size = self._get_pending_order_batch_size()
        ids = pending.ids
        for i in range(0, len(ids), batch_size):
            zort_batch = ids[i : i + batch_size]
            self._dispatch_pending_orders_batch(zort_batch)

    @api.model
    def _dispatch_pending_orders_batch(self, zort_batch):
        """Hook: process a batch of pending zort.order"""
        return self.browse(zort_batch).action_create_sale_order()

    def _hook_update_data(self, code_api, result):
        """
        Process Zort order sync after action_call_api fetches page 1.
        Handles pagination, sync log creation, and dispatching per-page work.

        Page-shifting protection: ``enddate`` is pinned to ``sync_to`` so that
        orders arriving during a long sync run do not push existing orders to
        later pages and cause gaps or duplicates.

        Extensibility: per-page dispatch is delegated to ``_dispatch_sync_page``
        so that add-on modules (e.g. zort_connector_queue) can override only
        that method to switch to asynchronous queue-job execution without
        touching this method.
        """
        if code_api != ZORT_GET_ORDER:
            return

        config = self._get_zort_api_config()
        ICP = self.env["ir.config_parameter"].sudo()
        sync_to = fields.Datetime.now()
        last_sync = ICP.get_param("zort_connector.last_sync_datetime", "")
        days_back = int(ICP.get_param("zort_connector.order_sync_days_back", 10))
        sync_from = (
            fields.Datetime.from_string(last_sync)
            if last_sync
            else sync_to - timedelta(days=days_back)
        )

        # Evaluate python_code once - single source of truth for API params.
        # Pin enddate to sync_to to create a stable query window; new orders
        # arriving during sync won't shift pages already fetched.
        base_payload = safe_eval(
            config.python_code or "{}",
            globals_dict=self._get_payload_globals_dict(),
        )
        base_payload.setdefault("enddate", sync_to.strftime("%Y-%m-%d"))

        # Demo mode: load page 1 from fixture instead of live API result
        if _DEMO_MODE:
            with open(os.path.join(_DEMO_DIR, "example1.json")) as f:
                result = json.load(f)

        counts = result.get("count") or 0
        total_pages = max((counts + 499) // 500, 1)
        sync_to_str = fields.Datetime.to_string(sync_to)

        # Create all sync-log records up-front so every page is visible
        # in the UI immediately (state=in_progress).
        all_pages = range(1, total_pages + 1)
        sync_logs = (
            self.env["zort.sync.log"]
            .sudo()
            .create(
                [
                    {
                        "sync_from": sync_from,
                        "sync_to": sync_to,
                        "page": page,
                        "total_pages": total_pages,
                        "state": "in_progress",
                    }
                    for page in all_pages
                ]
            )
        )

        for page in all_pages:
            self._dispatch_sync_page(
                sync_log_id=sync_logs[page - 1].id,
                page=page,
                total_pages=total_pages,
                base_payload=base_payload,
                sync_to_str=sync_to_str,
                # Pass the already-fetched result for page 1 to avoid a
                # redundant API call; pages > 1 must be fetched by the worker.
                page_result=result if page == 1 else None,
                is_last_page=(page == total_pages),
            )

    @api.model
    def _dispatch_sync_page(
        self,
        sync_log_id,
        page,
        total_pages,
        base_payload,
        sync_to_str,
        page_result,
        is_last_page,
    ):
        """Allow hook thif method"""
        self._process_sync_page(
            sync_log_id=sync_log_id,
            page=page,
            total_pages=total_pages,
            base_payload=base_payload,
            sync_to_str=sync_to_str,
            page_result=page_result,
            is_last_page=is_last_page,
        )

    @api.model
    def _process_sync_page(
        self,
        sync_log_id,
        page,
        total_pages,
        base_payload,
        sync_to_str,
        page_result,
        is_last_page,
    ):
        """
        Fetch (if needed) and upsert all orders for one page, then update the
        linked ``zort.sync.log`` record.

        This is the actual worker - safe to call directly or via a queue job.

        :param sync_log_id:   ID of the pre-created zort.sync.log record.
        :param page:          1-based page number to process.
        :param total_pages:   Total number of pages in this sync run.
        :param base_payload:  Base API query parameters (dict).
        :param sync_to_str:   Odoo-formatted datetime string for sync window end.
        :param page_result:   Pre-fetched result dict (page 1 only); None for
                              pages > 1 so the worker fetches it itself.
        :param is_last_page:  When True, advance ``last_sync_datetime`` on
                              successful completion.
        """
        sync_log = self.env["zort.sync.log"].sudo().browse(sync_log_id)
        config = self._get_zort_api_config()
        ICP = self.env["ir.config_parameter"].sudo()

        # Fetch data for pages > 1 (page 1 result is passed in directly).
        if page_result is None:
            try:
                if _DEMO_MODE:
                    with open(os.path.join(_DEMO_DIR, f"example{page}.json")) as f:
                        page_result = json.load(f)
                else:
                    response = self._execute_rest_api(
                        config,
                        auth_token=False,
                        payload={**base_payload, "page": page},
                    )
                    page_result = response.json()
            except Exception as e:
                msg = f"Page {page}/{total_pages} fetch failed: {e}"
                _logger.error("Zort sync: %s", msg)
                sync_log.write({"state": "failed", "error_message": msg})
                return

        created = updated = failed = 0
        for order_data in page_result.get("list", []):
            zort_order_id = str(order_data.get("id", ""))
            try:
                _, action = self._upsert_order(order_data, sync_log)
                if action == "created":
                    created += 1
                elif action == "updated":
                    updated += 1
            except Exception as e:
                failed += 1
                _logger.error("Failed to upsert Zort order %s: %s", zort_order_id, e)

        sync_log.write(
            {
                "state": "done",
                "order_created": created,
                "order_updated": updated,
                "order_failed": failed,
            }
        )

        # Only advance the sync cursor on the last page and when no orders
        # failed, so a partial failure retries from the same window next run.
        if is_last_page and failed == 0:
            ICP.set_param("zort_connector.last_sync_datetime", sync_to_str)
