import json
import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class ZortApi(models.AbstractModel):
    _name = "zort.api"
    _description = "Zort API Connector"

    def _log_api_response(self, msg, func, level="info", path="zort_api.py", line=0):
        """
        Logs the API response to the Odoo ir.logging model.

        Args:
            msg (dict): The JSON message data to be logged.
            func (str): The name of the function where the log is generated.
            level (str, optional): The log level (e.g., 'info', 'warning', 'error').
                Defaults to 'info'.
            path (str, optional): The file path to associate with the log entry.
                Defaults to 'zort_api.py'.
        """
        self.env["ir.logging"].create(
            {
                "name": "Zort API Response",
                "type": "server",
                "dbname": self.env.cr.dbname,
                "level": level,
                "message": json.dumps(msg),
                "path": path,
                "func": func,
                "line": line,
            }
        )

    def _get_api_url(self, endpoint):
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.endpoint_url")
        )
        return f"{base_url}/{endpoint}"

    def _get_header(self):
        """
        Returns the headers required for API requests.
        :return: dict - Headers for the API request.
        """
        HEADER = {
            "storename": self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.store_name"),
            "apikey": self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.api_key"),
            "apisecret": self.env["ir.config_parameter"]
            .sudo()
            .get_param("zort_connector.api_secret"),
        }
        return HEADER

    def _api_request(
        self,
        endpoint,
        method="GET",
        headers_extra=None,
        params=None,
        data=None,
        func_name="",
        line_number=0,
    ):
        """
        Generic method to handle API requests to Zort.

        :param endpoint: str - API endpoint (e.g., "Order/GetOrders")
        :param method: str - HTTP method ("GET" or "POST")
        :param headers_extra: dict - Additional headers to merge with base headers
        :param params: dict - Query parameters for GET or URL parameters for POST
        :param data: dict - JSON data for POST requests
        :param func_name: str - Name of the calling function for logging
        :param line_number: int - Line number for logging
        :return: dict - JSON response from the API or error dict
        """
        url = self._get_api_url(endpoint)
        headers = self._get_header().copy()

        if headers_extra:
            headers.update(headers_extra)

        try:
            timeout = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("zort_connector.limit_timeout", 10)
            )
            if method.upper() == "GET":
                response = requests.get(
                    url, headers=headers, params=params, timeout=timeout
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=headers,
                    params=params,
                    json=data if data else None,
                    timeout=timeout,
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            response_json = response.json()
            # on log return just number of record
            number_response = (
                len(response_json.get("list", [])) if "list" in response_json else 0
            )
            msg = {"success": True, "list_count": number_response}
            self._log_api_response(msg=msg, func=func_name, line=line_number)
            return response_json

        except requests.exceptions.RequestException as e:
            error_msg = {"error": str(e)}
            self._log_api_response(
                error_msg, func=func_name, level="error", line=line_number
            )
            _logger.error("Failed API request to %s: %s", endpoint, str(e))
            return {"error": str(e)}

    @api.model
    def _get_list_order(
        self, status: str = "0", orderidlist: str = "", numberlist: str = "", **kwargs
    ) -> dict:
        """
        Fetch a list of orders based on their status and optional filters.

        :param status: str - Status of the orders to fetch.
            Status codes:
            0 - Pending
            1 - Success
            2 - Voided
            3 - Waiting
            4 - Returned
            5 - Packed
            6 - Shipping
            7 - Failed Shipment
            Example: "0,1,3,4"
        :param orderidlist: str - Comma-separated list of order IDs to filter
            (optional).
        :param numberlist: str - Comma-separated list of order numbers to filter
            (optional).
        :param kwargs: Additional query parameters such as:
            - page: int - Page number
            - keyword: str - Keyword to search
            - createdafter: str - Filter orders created after this date (YYYY-MM-DD)
            - createdbefore: str - Filter orders created before this date (YYYY-MM-DD)
            - updatedafter: str - Filter orders updated after this date (YYYY-MM-DD)
            - updatedbefore: str - Filter orders updated before this date (YYYY-MM-DD)
            - orderdateafter: str - Filter orders with order date after (YYYY-MM-DD)
            - orderdatebefore: str - Filter orders with order date before (YYYY-MM-DD)
            - paymentafter: str - Filter orders with payment date after (YYYY-MM-DD)
            - paymentbefore: str - Filter orders with payment date before (YYYY-MM-DD)
            - fromamount: float - Minimum order amount
            - toamount: float - Maximum order amount
            - frompaymentamount: float - Minimum payment amount
            - topaymentamount: float - Maximum payment amount
            - limit: int - Limit number of results
        :return: dict - JSON response containing the list of orders.
        """
        headers_extra = {"orderidlist": orderidlist, "numberlist": numberlist}
        params = {"status": status}

        # Add any additional parameters from kwargs, filtering out None values
        for key, value in kwargs.items():
            if value is not None and value != "":
                params[key] = value

        return self._api_request(
            endpoint="Order/GetOrders",
            method="GET",
            headers_extra=headers_extra,
            params=params,
            func_name="_get_list_order",
            line_number=107,
        )

    @api.model
    def _add_product(self, data: dict) -> dict:
        """
        Add a new product to Zort.
        :param data: dict - JSON data containing product details.
        :return: dict - JSON response from the Zort API after adding the product.

        Note: Data structure should be like:
        {
            "sku": "P0014",
            "name": "Wit Day - Vitamin B",
            "sellprice": "20.00",
            "purchaseprice": "10.00",
            "unittext": "Piece",
            "weight": "500",
            "sell_vat_status": 2,
            "purchase_vat_status": 2
        }
        more details: https://developers.zortout.com/api-reference/product#add-product
        """
        return self._api_request(
            endpoint="Product/AddProduct",
            method="POST",
            data=data,
            func_name="_add_product",
            line_number=150,
        )

    @api.model
    def _update_product(self, zort_product_id: int, data: dict) -> dict:
        """
        Update an existing product in Zort.
        :param zort_product_id: int - The ID of the product in Zort to update.
        :param data: dict - JSON data containing updated product details.
        :note: Data structure should be like:
        {
            "name": "Wit Day - Vitamin B",
            "sellprice": "20.00",
            "purchaseprice": "10.00",
            "unittext": "Piece",
            "weight": "500",
            "sell_vat_status": 2,
            "purchase_vat_status": 2
        }
        :return: dict - JSON response from the Zort API after updating the product.
        """
        params = {"id": zort_product_id}
        return self._api_request(
            endpoint="Product/UpdateProduct",
            method="POST",
            params=params,
            data=data,
            func_name="_update_product",
            line_number=178,
        )

    @api.model
    def _update_product_available_stock_list(
        self, warehousecode: str, data: dict
    ) -> dict:
        """
        Update the available stock list for products in Zort.

        :param warehousecode: str - The warehouse code.
        :param data: dict - JSON payload with stock information.
            Example:
            {
            "stocks": [
                {
                "sku": "P0001",
                "stock": 10,
                "cost": 100
                }
            ]
            }
        :return: dict - JSON response from the Zort API.
        """
        params = {"warehousecode": warehousecode}
        return self._api_request(
            endpoint="Product/UpdateProductAvailableStockList",
            method="POST",
            params=params,
            data=data,
            func_name="_update_product_available_stock_list",
            line_number=219,
        )

    @api.model
    def _increase_product_stock_list(self, warehousecode: str, data: dict) -> dict:
        """
        Increase the stock of products in Zort.

        :param warehousecode: str - The warehouse code.
        :param data: dict - JSON payload with stock information.
            Example:
            {
            "stocks": [
                {
                "sku": "P0001",
                "stock": 10,
                "cost": 100
                }
            ]
            }
        :return: dict - JSON response from the Zort API.
        """
        params = {"warehousecode": warehousecode}
        return self._api_request(
            endpoint="Product/IncreaseProductStockList",
            method="POST",
            params=params,
            data=data,
            func_name="_increase_product_stock_list",
            line_number=260,
        )

    @api.model
    def _decrease_product_stock_list(self, warehousecode: str, data: dict) -> dict:
        """
        Decrease the stock of products in Zort.

        :param warehousecode: str - The warehouse code.
        :param data: dict - JSON payload with stock information.
            Example:
            {
            "stocks": [
                {
                "sku": "P0001",
                "stock": 10,
                "cost": 100
                }
            ]
            }
        :return: dict - JSON response from the Zort API.
        """
        params = {"warehousecode": warehousecode}
        return self._api_request(
            endpoint="Product/DecreaseProductStockList",
            method="POST",
            params=params,
            data=data,
            func_name="_decrease_product_stock_list",
            line_number=301,
        )

    @api.model
    def _get_return_orders(
        self, numberlist: str = "", returnorderidlist: str = "", **kwargs
    ) -> dict:
        """
        Fetch a list of return orders based on optional filters.

        :param numberlist: str - Comma-separated list of order numbers to filter
            (optional).
        :param returnorderidlist: str - Comma-separated list of return order IDs to
            filter (optional).
        :param kwargs: Additional query parameters such as:
            - returnorderdateafter: str - Return Order Date After (yyyy-MM-dd)
            - returnorderdatebefore: str - Return Order Date Before (yyyy-MM-dd)
            - fromamount: float - Minimum amount
            - toamount: float - Maximum amount
            - updatedatetimeafter: str - Updated Datetime After (yyyy-MM-dd HH:mm)
            - updatedatetimebefore: str - Updated Datetime Before (yyyy-MM-dd HH:mm)
            - createdatetimeafter: str - Created Datetime After (yyyy-MM-dd HH:mm)
            - createdatetimebefore: str - Created Datetime Before (yyyy-MM-dd HH:mm)
            - paymentafter: str - Paid Date After (yyyy-MM-dd)
            - paymentbefore: str - Paid Date Before (yyyy-MM-dd)
            - updatedafter: str - Updated Date After (yyyy-MM-dd)
            - updatedbefore: str - Updated Date Before (yyyy-MM-dd)
            - createdafter: str - Created Date After (yyyy-MM-dd)
            - createdbefore: str - Created Date Before (yyyy-MM-dd)
            - keyword: str - Keyword to search
            - createusername: str - Created by (Username)
            - warehousecode: str - Warehouse Code
            - topaymentamount: float - Maximum payment amount
            - frompaymentamount: float - Minimum payment amount
            - referenceid: int - Reference Order ID
            - referencenumber: str - Reference Order Number
            - limit: int - Limit per page (Max = 500)
            - page: int - Page (Default = 1)
        :return: dict - JSON response containing the list of return orders.
        """
        headers_extra = {
            "numberlist": numberlist,
            "returnorderidlist": returnorderidlist,
        }
        params = {}

        # Add any additional parameters from kwargs, filtering out None values
        for key, value in kwargs.items():
            if value is not None and value != "":
                params[key] = value

        return self._api_request(
            endpoint="ReturnOrder/GetReturnOrders",
            method="GET",
            headers_extra=headers_extra,
            params=params,
            func_name="_get_return_orders",
            line_number=346,
        )

    @api.model
    def _get_products(
        self, skulist: str = "", productidlist: str = "", **kwargs
    ) -> dict:
        """
        Fetch a list of products based on optional filters.

        :param skulist: str - Comma-separated list of SKUs to filter (optional).
        :param productidlist: str - Comma-separated list of product IDs to filter
            (optional).
        :return: dict - JSON response containing the list of products.
        :ref: https://developers.zortout.com/api-reference/product#get-products
        """
        headers_extra = {"skulist": skulist, "productidlist": productidlist}
        params = {}

        # Add any additional parameters from kwargs, filtering out None values
        for key, value in kwargs.items():
            if value is not None and value != "":
                params[key] = value

        return self._api_request(
            endpoint="Product/GetProducts",
            method="GET",
            headers_extra=headers_extra,
            params=params,
            func_name="_get_products",
            line_number=392,
        )
