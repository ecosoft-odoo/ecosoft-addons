Zort Connector for Odoo

Integrates Odoo with Zort e-commerce platform for bidirectional synchronization of orders, products, inventory, and returns.

**5 Main Zort API Endpoints Used:**

1. **Add Product API** - Create products in Zort from Odoo
2. **Update Product API** - Update product information in Zort
3. **Update Stock API** - Sync inventory quantities to Zort
4. **Get Orders API** - Import orders from Zort to Odoo
5. **Get Return Orders API** - Process return orders from Zort

**Key Features**

* **Order Management**: Automatic import every 10 minutes with status mapping (Pending→Draft, Waiting→Confirmed, Success→Delivered+Invoiced, Voided→Cancelled)
* **Product Sync**: Create/update products in Zort with SKU matching
* **Stock Sync**: Real-time inventory updates on picking validation
* **Returns Processing**: Automatic return picking creation and credit notes
* **Multi-platform Support**: Lazada, Shopee, Magento integration
* **Robust Logging**: Complete API request/response tracking

**Requirements**

* Odoo 18.0+
* Zort API credentials (Key, Secret, Store Name)
* Valid SKUs (default_code) on products

**Quick Setup**

1. Enable Zort Connector in Settings
2. Configure API credentials
3. Mark products "Sync with Zort"
4. Scheduled actions handle automatic synchronization
