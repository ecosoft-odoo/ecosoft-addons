# Copyright 2025 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class LINEService(models.AbstractModel):
    _inherit = "line.service"

    def _split_data(self, data):
        def try_convert(value):
            try:
                float_value = float(value)  # Try to convert to float first
                if float_value.is_integer():  # Check if the float is a whole number
                    return int(float_value)  # Convert to integer if it is
                else:
                    return float_value  # Return as float if it has a fractional part
            except ValueError:
                return value  # If conversion fails, return the original value

        # Step 1: Split by '&' to separate key-value pairs
        pairs = data.split("&")

        # Step 2: Split each pair by '=' to separate keys and values
        result = {}
        for pair in pairs:
            key, value = pair.split("=")
            result[key] = try_convert(value)
        return result

    def _action_postback(self, event):
        result = self._split_data(event.postback.data)
        model = result.get("model")
        res_id = result.get("res_id")
        method = result.get("method")
        obj = self.env[model].browse(res_id)
        return getattr(obj, method)(event, result)
