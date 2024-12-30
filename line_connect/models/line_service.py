# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

import requests

from odoo import _, api, fields, models

TIMEOUT = 20
_logger = logging.getLogger(__name__)


class LINEService(models.AbstractModel):
    _name = "line.service"
    _description = "Common function for LINE Service"

    @api.model
    def _do_request(
        self, uri, params=None, headers=None, method="POST", timeout=TIMEOUT
    ):
        """Execute the request to LINE API.
        Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param uri : the url to contact
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param method : the method to use to make the request
        """
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        _logger.debug(
            "Uri: %s - Type : %s - Headers: %s - Params : %s !",
            uri,
            method,
            headers,
            params,
        )
        ask_time = fields.Datetime.now()
        try:
            if method.upper() in ("GET", "DELETE"):
                res = requests.request(
                    method.lower(), uri, params=params, timeout=timeout
                )
            elif method.upper() in ("POST", "PATCH", "PUT"):
                res = requests.request(
                    method.lower(), uri, data=params, headers=headers, timeout=timeout
                )
            else:
                raise Exception(
                    _(
                        "Method not supported [%s] not in "
                        "[GET, POST, PUT, PATCH or DELETE]!"
                    )
                    % (method)
                )
            res.raise_for_status()
            status = res.status_code

            if int(status) == 204:  # Page not found, no response
                response = False
            else:
                response = res.json()

            try:
                ask_time = datetime.strptime(
                    res.headers.get("date", ""), "%a, %d %b %Y %H:%M:%S %Z"
                )
            except ValueError:
                _logger.exception("ValueError: %s", res.headers.get("date", ""))
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad line request : %s !", error.response.content)
                raise error
        return (status, response, ask_time)
