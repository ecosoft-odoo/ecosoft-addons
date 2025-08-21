Zort Connector - E-commerce Integration for Odoo
=================================================

The Zort Connector module provides seamless integration between Odoo and the Zort e-commerce platform, enabling businesses to synchronize their online sales operations with their ERP system.

Key Features
------------

**Bidirectional Data Synchronization**
  * Orders: Automatic import from Zort to Odoo with real-time status updates
  * Products: Create and update products in Zort from Odoo
  * Inventory: Real-time stock quantity synchronization

**Order Management**
  * Automatic creation of sale orders from Zort orders
  * Support for multiple e-commerce platforms (Magento, Lazada, Shopee, etc.)
  * Intelligent customer matching and creation
  * Handling of shipping fees, discounts, and taxes
  * Order status synchronization (pending, confirmed, delivered, cancelled)

**Product Synchronization**
  * Create new products in Zort directly from Odoo
  * Update product information (name, price, description)
  * Sync stock quantities across platforms
  * Support for SKU-based product matching

**Inventory Management**
  * Automatic stock updates when shipments are validated
  * Batch stock synchronization capabilities
  * Support for multiple warehouses
  * Real-time inventory tracking

**Customer Management**
  * Automatic customer creation from marketplace orders
  * Platform-specific customer handling
  * Customer matching by phone number (Magento)
  * Default marketplace customer fallback

**Automated Processes**
  * Scheduled order imports every 10 minutes
  * Automatic order status updates
  * Real-time inventory synchronization
  * Background processing for large data sets

Technical Capabilities
----------------------

**API Integration**
  * Full Zort API v4 support
  * Robust error handling and logging
  * Configurable timeout settings
  * Comprehensive API response logging

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
---------

This module is ideal for businesses that:

* Sell products through Zort-connected marketplaces
* Need real-time inventory synchronization across platforms
* Want to centralize order management in Odoo
* Require automated e-commerce operations
* Manage multi-channel sales operations

Supported Platforms
-------------------

The connector supports orders from various e-commerce platforms connected to Zort:

* Magento
* Lazada
* Shopee
* And other Zort-integrated marketplaces

Requirements
------------

* Odoo 18.0+
* Active Zort account with API access
* Valid API credentials (API Key, API Secret, Store Name)
* Internet connectivity for API communication

Getting Started
---------------

1. Install the module
2. Configure API credentials in Settings
3. Set up product synchronization
4. Enable automatic order import
5. Monitor operations through logging

The module includes comprehensive documentation and examples to help you get started quickly with your Zort integration.
