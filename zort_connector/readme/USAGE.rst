Zort Connector Usage Guide

Overview

The Zort Connector module enables seamless integration between Odoo and the Zort e-commerce platform. It provides comprehensive bidirectional synchronization of orders, products, inventory data, and return orders with advanced automation capabilities.

Configuration

**Initial Setup**

1. **Enable Zort Connector**

   Navigate to Settings → General Settings → Zort Connector section:

   - Check "Enable Zort Connector"
   - Configure your Zort API credentials:

     * **Zort Endpoint URL**: Default is ``https://open-api.zortout.com/v4``
     * **Zort API Key**: Your API key from Zort dashboard
     * **Zort API Secret**: Your API secret from Zort dashboard
     * **Zort Store Name**: Your store identifier in Zort
     * **Zort Warehouse Code**: Default is ``W0001``

2. **Verify Configuration**

   Ensure all credentials are correctly entered. The module will use these for all API communications with Zort.

Features and Usage

Product Management

**Creating Products in Zort**

1. Navigate to Inventory → Products → Products
2. Open any product you want to synchronize
3. Enable "Sync with Zort" checkbox
4. Click "Create Product on Zort" button
5. The system will:
   - Send product data (SKU, name, sell price, purchase price, unit) to Zort
   - Mark the product as "Created on Zort"
   - Store the Zort Product ID for future updates
   - Add a log note with success/error status

**Updating Products in Zort**

1. Open a product that's already created on Zort (shows "Created on Zort" = True)
2. Make your changes (name, list price, standard price, unit of measure)
3. Click "Update Product to Zort" button
4. The system will sync the updated information to Zort
5. A log note will be added showing the update status

**Stock Quantity Synchronization**

The module automatically syncs stock quantities in several ways:

- **Automatic Sync on Picking Validation**: When you validate any stock picking, quantities are automatically synced
- **Manual Sync**: Use server actions to manually sync stock quantities
- **Real-time Updates**: Only products marked as "Created on Zort" will have their stock synced

Stock Operations:
- **Incoming operations**: Increase stock in Zort
- **Outgoing operations**: Decrease stock in Zort
- **Internal operations**: No stock sync performed

Order Management

**Automatic Order Import**

The system automatically imports orders from Zort every 10 minutes using scheduled actions:

1. **New Order Creation**:
   - Fetches orders from Zort based on status filters
   - Creates sale orders in Odoo with proper customer assignment
   - Handles shipping fees, discounts, and product lines
   - Stores complete Zort order data for reference

2. **Order Status Updates**:
   - Updates existing orders with latest status from Zort
   - Triggers workflow actions based on status:
   **"Voided"**: Cancels the sale order
   **"Waiting"**: Confirms the sale order
   **"Success"**: Confirms order, validates deliveries, and creates draft invoice

**Customer Handling**

The module intelligently manages customers:

- Creates marketplace-specific customers for each platform
- Uses customer platform codes to identify source (e.g., "lazada", "shopee")
- Falls back to default marketplace customer if specific customer not found
- Preserves customer data from Zort orders

**Manual Order Processing**

You can also manually trigger order processing:

1. Navigate to Sales → Actions → Server Actions
2. Select "Process Sales Order from Zort" action
3. The system will fetch and process pending orders

Return Order Management

**Automatic Return Processing**

The system processes return orders automatically every 10 minutes:

1. **Pending Returns**:
   - Creates return pickings for orders with "Pending" status
   - Matches returned items with original order lines
   - Sets up proper quantities based on Zort return data
   - Stores return order number and data

2. **Success Returns**:
   - Validates return pickings for orders with "Success" status
   - Creates credit notes with accurate pricing from return data
   - Reconciles with original invoices

**Return Order Data**

Each return picking stores:
- **Zort Return Number**: The return order identifier from Zort
- **Zort Return Data**: Complete JSON data from Zort return order
- **Return Status**: Current status of the return process

**Viewing Return Data**

1. Open any return picking with Zort return data
2. Click "View Return Order JSON" button
3. A new window will display the complete return order data from Zort

Monitoring and Logging

**API Response Logging**

All API communications are logged in the system:

1. Navigate to Settings → Technical → Logging
2. Filter by "Zort API Response" to see all API interactions
3. Each log entry contains:
   - Function name that made the API call
   - Complete request/response data
   - Error messages if any
   - Timestamp and line number information

**Order and Return Tracking**

Each sale order and return picking contains:
- **Order Data**: Complete Zort order information in JSON format
- **Status Information**: Current Zort status and payment status
- **Tracking Fields**: Zort order ID, number, and related data

**Error Handling**

The module includes comprehensive error handling:
- API timeout protection (10-second timeout)
- Automatic retry mechanisms
- Detailed error logging with context
- Graceful degradation for failed operations
- User-friendly error messages in log notes

Advanced Features

**Scheduled Actions**

Two main scheduled actions run every 10 minutes:

1. **Auto Sync Zort Order**:
   - Model: sale.order
   - Method: process_sales_order_from_zort()
   - Imports new orders and updates existing ones

2. **Auto Sync Zort Return Order**:
   - Model: stock.picking
   - Method: action_create_return_picking()
   - Processes return orders from Zort

**Data Integration Points**

- **Sale Orders**: Extended with Zort-specific fields and methods
- **Products**: Enhanced with Zort synchronization capabilities
- **Stock Pickings**: Enhanced with return order processing
- **Partners**: Extended with customer platform tracking
- **Settings**: Centralized Zort configuration management

**Web Controllers**

The module provides web endpoints for data viewing:
- ``/zort_connector/view_zort_order_json/<order_id>``: View order JSON data
- ``/zort_connector/view_zort_return_order_json/<picking_id>``: View return JSON data

Troubleshooting

**Common Issues**

1. **API Connection Errors**:
   - Verify endpoint URL, API key, and secret
   - Check network connectivity
   - Review API response logs

2. **Product Sync Issues**:
   - Ensure products have valid SKUs (default_code)
   - Check "Sync with Zort" flag is enabled
   - Verify Zort Product ID is set for updates

3. **Order Import Problems**:
   - Check scheduled actions are active
   - Verify customer data and product SKUs exist
   - Review error logs for specific issues

4. **Return Processing Issues**:
   - Ensure original sale orders exist in Odoo
   - Check return order data integrity
   - Verify picking validation process

**Best Practices**

- Regularly monitor API response logs
- Test product synchronization with a few products first
- Ensure proper SKU management across systems
- Monitor scheduled action execution
- Keep Zort credentials secure and up-to-date

**Automatic Order Import**

The module automatically imports orders from Zort via scheduled actions that run every 10 minutes.

**Manual Order Import**

You can manually trigger order import using server actions.

**Order Status Mapping**

The system handles different Zort order statuses:
- Pending: Creates draft sale orders
- Waiting: Confirms the sale order
- Success: Validates delivery and creates draft invoice
- Voided: Cancels the sale order

**Customer Handling**

The module intelligently handles customers based on the platform type.

Inventory Synchronization

**Automatic Stock Updates**

Stock quantities are automatically synced to Zort when validating shipments.

**Manual Stock Sync**

You can manually trigger sync using the "Sync Qty to Zort" server action.

API Methods Available

The module provides various API methods for integration with comprehensive error handling and logging.

Data Flow

Orders are fetched from Zort API, products are matched by SKU, customers are created/matched based on platform, and sale orders are created with appropriate status.

Troubleshooting

**Common Issues**

1. Product not found: Ensure the SKU exists in Odoo
2. API authentication errors: Verify your API credentials in settings
3. Stock sync failures: Check warehouse code configuration
4. Order import failures: Verify required products exist with correct SKUs

**Logging**

All API interactions are logged for debugging purposes.

**Viewing Order Data**

For Zort orders, you can view the raw JSON data by clicking "View Zort Order JSON" button on the sale order form.

Customization

You can customize product synchronization and order processing logic by extending the existing methods.

Security Notes

API credentials are stored in system parameters and all operations are logged for audit purposes.

Performance Considerations

Orders are imported in batches, stock updates are processed asynchronously, and API rate limits are respected.

1. Navigate to Inventory → Products → Products
2. Open any product you want to sync
3. Check "Sync with Zort" field
4. Click "Create Product on Zort" button
5. The system will:

   - Send product data (SKU, name, prices, unit) to Zort
   - Mark the product as "Created on Zort"
   - Store the Zort Product ID for future updates

**Updating Products in Zort**

1. Open a product that's already created on Zort
2. Make your changes (name, prices, unit)
3. Click "Update Product to Zort" button
4. The system will sync the updated information

**Updating Stock Quantities**

1. Open a product created on Zort
2. Click "Update Qty to Zort" button
3. The current ``qty_available`` will be synced to Zort

Order Management
~~~~~~~~~~~~~~~~

**Automatic Order Import**

The module automatically imports orders from Zort via scheduled actions:

- **Auto Zort Order Import**: Runs every 10 minutes to fetch new orders
- **Auto Update Zort Order**: Runs every 10 minutes to update existing order statuses

**Manual Order Import**

You can manually trigger order import using server actions or by calling::

    # Import pending orders
    self.env['sale.order'].create_sales_order_from_zort(status="0")

    # Import orders with specific status
    self.env['sale.order'].create_sales_order_from_zort(status="0,1,3")

**Order Status Mapping**

The system handles different Zort order statuses:

- **Pending (0)**: Creates draft sale orders
- **Waiting (3)**: Confirms the sale order
- **Success (1)**: Validates delivery and creates draft invoice
- **Voided (2)**: Cancels the sale order

**Customer Handling**

The module intelligently handles customers:

- **Magento Orders**: Creates individual customers based on phone numbers
- **Other Platforms**: Uses platform-specific default customers
- **Fallback**: Uses a default marketplace customer

Inventory Synchronization
~~~~~~~~~~~~~~~~~~~~~~~~~

**Automatic Stock Updates**

Stock quantities are automatically synced to Zort when:

- Validating incoming shipments (increases stock)
- Validating outgoing deliveries (decreases stock)
- Manual product quantity updates

**Manual Stock Sync**

For stock pickings, you can manually trigger sync using the "Sync Qty to Zort" server action.

API Methods Available
---------------------

The module provides various API methods for integration:

Product API
~~~~~~~~~~~

.. code-block:: python

    # Add product to Zort
    response = self._add_product({
        "sku": "P001",
        "name": "Product Name",
        "sellprice": "100.00",
        "purchaseprice": "50.00",
        "unittext": "Piece"
    })

    # Update product in Zort
    response = self._update_product(zort_product_id, {
        "name": "Updated Name",
        "sellprice": "120.00"
    })

    # Update stock quantities
    response = self._update_product_available_stock_list("W0001", {
        "stocks": [{"sku": "P001", "stock": 100}]
    })

Order API
~~~~~~~~~

.. code-block:: python

    # Get orders with filters
    response = self._get_list_order(
        status="0,1",
        page=1,
        limit=100,
        createdafter="2024-01-01",
        keyword="INV-2024"
    )

    # Get return orders
    response = self._get_return_orders(
        returnorderdateafter="2024-01-01",
        limit=50
    )

Data Flow
---------

**Zort → Odoo (Import)**

1. Orders are fetched from Zort API
2. Products are matched by SKU (``default_code``)
3. Customers are created/matched based on platform
4. Sale orders are created with appropriate status
5. Order lines include products, shipping fees, and discounts

**Odoo → Zort (Export)**

1. Products are created/updated in Zort
2. Stock movements trigger quantity updates
3. Inventory changes are synced in real-time

Troubleshooting
---------------

**Common Issues**

1. **Product not found**: Ensure the SKU (``default_code``) exists in Odoo
2. **API authentication errors**: Verify your API credentials in settings
3. **Stock sync failures**: Check warehouse code configuration
4. **Order import failures**: Verify required products exist with correct SKUs

**Logging**

All API interactions are logged to ``ir.logging`` for debugging:

- Successful API responses
- Error messages with details
- Request/response data for troubleshooting

**Viewing Order Data**

For Zort orders, you can view the raw JSON data by clicking "View Zort Order JSON" button on the sale order form.

Customization
-------------

**Extending Product Data**

You can customize product synchronization by modifying the data structure in ``action_create_product_on_zort()``:

.. code-block:: python

    data = {
        "sku": self.default_code,
        "name": self.name,
        "sellprice": self.list_price,
        "purchaseprice": self.standard_price,
        "unittext": self.uom_name,
        "weight": self.weight,  # Uncomment to sync weight
        "sell_vat_status": 2,   # Add VAT status
    }

**Custom Order Processing**

Override ``_create_or_update_sale_order()`` to customize order processing logic.

**Additional API Endpoints**

The generic ``_api_request()`` method can be used to call any Zort API endpoint:

.. code-block:: python

    response = self._api_request(
        endpoint="Custom/Endpoint",
        method="POST",
        data=custom_data,
        func_name="custom_function"
    )

