import logging
from odoo import _, api, fields, models, exceptions

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'zort.api']

    # This field can be used to store the Zort order ID
    is_zort_order = fields.Boolean(
        string='Is Zort Order',
        help='Indicates if this sale order is created from Zort.',
        default=False,
        # readonly=True,
    )
    zort_order_id = fields.Char(
        string='Zort Order ID',
        help='The ID of the order in Zort.',
        copy=False,
        # readonly=True,
    )
    zort_order_number = fields.Char(
        string='Zort Order Number',
        help='The order number in Zort.',
        copy=False,
        # readonly=True,
    )
    zort_order_status = fields.Char(
        string='Zort Order Status',
        help='The status of the order in Zort.',
        copy=False,
        # readonly=True,
    )

    @api.model
    def create_sales_order_from_zort(self, status="0", orderidlist="", numberlist=""):
        """
        Fetch orders from Zort based on the provided status and optional filters.
        :param status: str - Status of the orders to fetch.
        :param orderidlist: str - Comma-separated list of order IDs to filter (optional).
        :param numberlist: str - Comma-separated list of order numbers to filter (optional).
        :return: dict - JSON response containing the list of orders.
        """
        try:
            response = self._get_list_order(status, orderidlist, numberlist)
        except Exception as e:
            _logger.error("Error fetching Zort orders: %s", e)

        if response.get('count') == 0:
            _logger.warning("No orders fetched from Zort for the given criteria.")
            return

        orders = response.get("list", [])
        for order in orders:
            try:
                self._create_or_update_sale_order(order)
                self._log_api_response(response_json={
                    'order_id': order.get('id'),
                    'status': order.get('status'),
                    'message': 'Sale Order created successfully'
                }, func='create_sales_order_from_zort', path='zort_connector/models/sale_order.py', line=37)
            except Exception as e:
                _logger.error("Error creating/updating sale order: %s", e)
                self._log_api_response(response_json={
                    'order_id': order.get('id'),
                    'status': order.get('status'),
                    'error': str(e)
                }, func='create_sales_order_from_zort', level='error', path='zort_connector/models/sale_order.py', line=37)

    def _create_or_update_sale_order(self, order):
        """
        Create or update a sale order based on the Zort order data.
        :param order: dict - The Zort order data.
        """
        # Check if the order already exists in Odoo
        existing_order = self.search([('zort_order_id', '=', order.get('id'))], limit=1)
        if existing_order:
            # Update existing order
            existing_order.write({
                'zort_order_number': order.get('number'),
                'zort_order_status': order.get('status'),
            })
            _logger.info("Updated Sale Order: %s", existing_order.name)
            return

        else:
            # Create a new sale order
            _logger.info("Creating Sale Order for Zort Order ID: %s", order.get('id'))

            # Prepare the data for the sale order
            order_data = {
                'partner_id': self.env.ref('zort_connector.marketplace_customer').id,  # a default customer
                'is_zort_order': True,
                'zort_order_id': order.get('id'),
                'zort_order_number': order.get('number'),
                'zort_order_status': order.get('status'),
            }

            # Create the sale order
            sale_order = self.create(order_data)

            # Add order lines
            order_lines = []
            for line in order.get('list', []):
                product = self.env['product.product'].search([('default_code', '=', line.get('sku'))], limit=1)
                if not product:
                    _logger.warning("Product with SKU %s not found. Skipping line.", line.get('sku'))
                    continue
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': line.get('number', 1),
                    'price_unit': line.get('totalprice', 0.0),
                    'name': line.get('name', product.name),
                }))

            # check if there is shipping fee
            if order.get('shippingamount', 0.0) > 0:
                shipping_fee_product = self.env['product.product'].search([('default_code', '=', 'shipping_fee')], limit=1)
                order_lines.append((0, 0, {
                    'product_id': shipping_fee_product.id,
                    'product_uom_qty': 1,
                    'price_unit': order.get('shippingamount', 0.0),
                    'name': "Shipping Fee",
                }))

            # check if there is discount
            if order.get('discountamount', 0.0) > 0:
                discount_product = self.env['product.product'].search([('default_code', '=', 'zort_discount')], limit=1)
                order_lines.append((0, 0, {
                    'product_id': discount_product.id,
                    'product_uom_qty': 1,
                    'price_unit': -order.get('discountamount', 0.0),
                    'name': "Discount",
                }))

            if order_lines:
                sale_order.order_line = order_lines

            _logger.info("Created Sale Order: %s", sale_order.name)

        return sale_order

