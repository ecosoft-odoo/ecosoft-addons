import json
import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class ZortApi(models.AbstractModel):
    _name = "zort.api"
    _description = "Zort API Connector"

    def _log_api_response(
        self, response_json, func, level="info", path="zort_api.py", line=0
    ):
        """
        Logs the API response to the Odoo ir.logging model.

        Args:
            response_json (dict): The JSON response data to be logged.
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
                "message": json.dumps(response_json),
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

    @api.model
    def _get_list_order(
        self, status: str = "0", orderidlist: str = "", numberlist: str = ""
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
        :return: dict - JSON response containing the list of orders.
        """
        url = self._get_api_url("Order/GetOrders")
        HEADER = self._get_header()
        headers = HEADER.copy()
        headers.update({"orderidlist": orderidlist, "numberlist": numberlist})

        params = {
            # "page": 1,
            # "keyword": "IV-2020",
            # "createdafter": "2020-12-24",
            # "createdbefore": "2020-12-27",
            # "updatedafter": "2021-06-10",
            # "updatedbefore": "2021-01-30",
            # "orderdateafter": "2020-12-15",
            # "orderdatebefore": "2020-12-15",
            # "paymentafter": "2020-12-15",
            # "paymentbefore": "2020-12-15",
            "status": status,
            # "fromamount": 0,
            # "toamount": 10000,
            # "frompaymentamount": 0,
            # "topaymentamount": 10000,
            # "limit": 2
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            response_json = response.json()
            self._log_api_response(response_json, func="_get_list_order", line=52)
            return response_json

        except requests.exceptions.RequestException as e:
            error_msg = {"error": str(e)}
            self._log_api_response(
                error_msg, func="_get_list_order", level="error", line=52
            )
            _logger.error("Failed to retrieve orders from Zort API: %s", str(e))
            return {"error": str(e)}

    @api.model
    def _update_product_available_stock_list(self, warehouse: str, data: dict) -> dict:
        pass

    @api.model
    def _get_products(self, sku: str = "") -> dict:
        pass

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

        url = self._get_api_url("Product/AddProduct")
        HEADER = self._get_header()
        headers = HEADER.copy()
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(data), timeout=10
            )
            response.raise_for_status()
            response_json = response.json()
            self._log_api_response(response_json, func="_add_product", line=118)
            return response_json
        except requests.RequestException as e:
            error_msg = {"error": str(e)}
            self._log_api_response(
                error_msg, func="_add_product", level="error", line=118
            )
            _logger.error("Failed to add product to Zort: %s", str(e))
            return {"error": str(e)}

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
        url = self._get_api_url("Product/UpdateProduct")
        HEADER = self._get_header()
        headers = HEADER.copy()
        PARAMS = {
            "id": zort_product_id,
        }
        try:
            response = requests.post(
                url, headers=headers, params=PARAMS, data=json.dumps(data), timeout=10
            )
            response.raise_for_status()
            response_json = response.json()
            self._log_api_response(response_json, func="_update_product", line=178)
            return response_json
        except requests.RequestException as e:
            error_msg = {"error": str(e)}
            self._log_api_response(
                error_msg, func="_update_product", level="error", line=178
            )
            _logger.error("Failed to update product in Zort: %s", str(e))
            return {"error": str(e)}
