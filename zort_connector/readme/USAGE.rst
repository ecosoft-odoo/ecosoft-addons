Zort Connector Usage Guide
==========================

Overview
--------

The Zort Connector module enables seamless integration between Odoo and the Zort e-commerce platform. It provides bidirectional synchronization of orders, products, and inventory data.

Configuration
-------------

1. **Enable Zort Connector**

   Navigate to Settings → General Settings → Zort Connector section:
   
   - Check "Enable Zort Connector"
   - Enter your Zort API credentials:
     
     * **Zort Endpoint URL**: Default is ``https://open-api.zortout.com/v4``
     * **Zort API Key**: Your API key from Zort
     * **Zort API Secret**: Your API secret from Zort  
     * **Zort Store Name**: Your store name in Zort

2. **Product Configuration**

   Before syncing products, ensure your warehouse code is properly configured. The default warehouse code used is ``W0001``.

Features and Usage
------------------

Product Management
~~~~~~~~~~~~~~~~~~

**Creating Products in Zort**

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

Security Notes
--------------

- API credentials are stored in system parameters
- Only users with appropriate permissions can configure the connector
- API calls are logged for audit purposes
- Customer data is handled according to privacy requirements

Performance Considerations
--------------------------

- Orders are imported in batches to avoid timeouts
- Stock updates are processed asynchronously when possible
- API rate limits are respected through timeout settings
- Large product catalogs should be synced in smaller batches
