Zort Connector for Odoo

The Zort Connector module provides seamless integration between Odoo and the Zort e-commerce platform, enabling businesses to synchronize their online sales operations with their ERP system. This connector facilitates bidirectional data flow between Odoo and Zort for orders, products, inventory, and returns management.

Key Features

**Order Management & Synchronization**
  * Automatic import of Zort orders to Odoo sale orders with comprehensive status mapping
  * Support for multiple order statuses: Pending, Waiting, Success, Voided, Returned, Packed, Shipping, Failed Shipment
  * Intelligent workflow automation based on order status changes
  * Automatic order confirmation for "Waiting" status orders
  * Automatic delivery validation and invoice creation for "Success" status orders
  * Order cancellation handling for "Voided" status orders
  * Integration with shipping fees, discounts, and tax calculations
  * Real-time order status updates and synchronization

**Product Synchronization**
  * Create new products in Zort directly from Odoo product templates
  * Update existing product information (name, sell price, purchase price, unit text)
  * SKU-based product matching and synchronization
  * Support for product weight and VAT status configuration
  * Selective product synchronization with "Sync with Zort" flag
  * Product creation status tracking with Zort product ID mapping

**Advanced Inventory Management**
  * Real-time stock quantity synchronization for incoming and outgoing operations
  * Automatic stock updates when stock pickings are validated
  * Support for stock increase/decrease operations based on picking type
  * Warehouse-specific stock management with configurable warehouse codes
  * Intelligent stock sync only for products created on Zort platform
  * Prevention of duplicate stock updates for Zort-originated orders

**Return Order Processing**
  * Comprehensive return order management from Zort
  * Automatic creation of return pickings for "Pending" return orders
  * Automatic validation of return pickings for "Success" return orders
  * Intelligent return picking detection to prevent duplicates
  * Return order data preservation with JSON storage
  * Credit note generation for processed returns with accurate pricing
  * Return order tracking with Zort return numbers

**Customer & Partner Management**
  * Automatic customer creation from marketplace orders
  * Platform-specific customer handling with customer platform codes
  * Support for multiple e-commerce platforms (Lazada, Shopee, etc.)
  * Intelligent customer matching and fallback mechanisms
  * Marketplace customer data integration

**Automated Processes & Scheduling**
  * Scheduled order imports every 10 minutes via automated cron jobs
  * Scheduled return order processing every 10 minutes
  * Background processing for large data sets with robust error handling
  * Configurable date ranges for order and return order fetching
  * Automatic retry mechanisms for failed API operations

**Technical Capabilities**

**Robust API Integration**
  * Full Zort API v4 support with comprehensive endpoint coverage
  * Advanced error handling and logging with ir.logging integration
  * Configurable timeout settings (10-second default)
  * Request/response logging for debugging and audit trails
  * Support for GET and POST HTTP methods with proper data handling
  * Header-based authentication with store name, API key, and secret

**Data Management & Controllers**
  * JSON data viewers for order and return order inspection
  * Web controllers for data visualization and debugging
  * Comprehensive data validation and error recovery
  * Support for large JSON payloads with proper serialization

**Configuration & Security**
  * Centralized configuration through Odoo settings
  * Secure credential storage with password fields
  * Configurable endpoint URLs and warehouse codes
  * Environment-specific configuration support

**Data Security**
  * Secure API credential storage
  * Audit logging for all operations
  * Role-based access control
  * Data validation and error handling

**Flexibility**
  * Configurable synchronization rules
  * Customizable order processing logic
  * Extensible product data mapping
  * Support for custom API endpoints

**Performance**
  * Batch processing capabilities
  * Asynchronous operations where possible
  * Optimized database queries
  * Rate limiting compliance

Use Cases

This module is ideal for businesses that:

* Sell products through Zort-connected marketplaces
* Need real-time inventory synchronization across platforms
* Want to centralize order management in Odoo
* Require automated e-commerce operations
* Manage multi-channel sales operations

Supported Platforms

The connector supports orders from various e-commerce platforms connected to Zort:

* Magento
* Lazada
* Shopee
* And other Zort-integrated marketplaces

Requirements

* Odoo 18.0+
* Active Zort account with API access
* Valid API credentials (API Key, API Secret, Store Name)
* Internet connectivity for API communication

Getting Started

1. Install the module
2. Configure API credentials in Settings
3. Set up product synchronization
4. Enable automatic order import
5. Monitor operations through logging

The module includes comprehensive documentation and examples to help you get started quickly with your Zort integration.
