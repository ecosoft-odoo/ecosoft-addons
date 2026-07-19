# Copyright 2025 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import ssl
import xmlrpc.client

import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class CommonBaseApi(models.AbstractModel):
    _name = "common.base.api"
    _description = "Common Base API"

    api_log_ids = fields.One2many(
        comodel_name="api.connector.log",
        inverse_name="res_id",
        domain=lambda self: [("res_model", "=", self._name)],
        string="API Logs",
        readonly=True,
    )
    api_log_count = fields.Integer(
        compute="_compute_api_log_count",
    )
    api_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("failed", "Failed"),
            ("success", "Success"),
        ],
        default="draft",
        string="API Status",
        copy=False,
    )
    api_result = fields.Text(string="API Result", copy=False)
    callback_status = fields.Selection(
        [("none", "None"), ("success", "Success"), ("failed", "Failed")],
        default="none",
        copy=False,
    )

    @api.depends("api_log_ids")
    def _compute_api_log_count(self):
        counts = self.env["api.connector.log"].read_group(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)],
            ["res_id"],
            ["res_id"],
        )
        count_map = {r["res_id"]: r["res_id_count"] for r in counts}
        for rec in self:
            rec.api_log_count = count_map.get(rec.id, 0)

    def action_view_api_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("API Logs"),
            "res_model": "api.connector.log",
            "view_mode": "list,form",
            "domain": [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
            ],
        }

    def _notify_user(self, ttype, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": ttype,
                "message": message,
                # NOTE: If it call from wizard
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _write_failed_state(self, result):
        """Write failed state to record. Override to add custom failure behavior."""
        return self.write({"api_status": "failed", "api_result": result})

    def _hook_on_failed(self, code_api, error_msg):
        """Hook called after a failed API call. Override to handle failure."""
        return

    def _get_latest_api_log(self):
        """Return the most recent API log of this record, ordered by call
        date with id as tie-breaker for logs created within the same second."""
        self.ensure_one()
        return self.api_log_ids.sorted(
            key=lambda log: (log.create_date, log.id), reverse=True
        )[:1]

    def _truncate_text(self, text, limit=None):
        """Helper: truncate text for safe storage.

        The limit comes from the ``api_connector.log_limit`` system
        parameter (0 = keep full text, the default) unless explicitly
        passed by the caller."""
        if not text:
            return text
        text = str(text)
        if limit is None:
            limit = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("api_connector.log_limit", "0")
            )
        return text[:limit] if limit > 0 else text

    def _get_header_globals_dict(self, auth_token):
        return {"auth_token": auth_token, "rec": self, "env": self.env}

    def _get_payload_globals_dict(self):
        return {
            "rec": self,
            "env": self.env,
            "today": fields.Date.context_today(self),
            "today_datetime": fields.Datetime.context_timestamp(
                self, fields.Datetime.now()
            ),
        }

    def _eval_config_value(self, value):
        """Evaluate a config field as a Python expression
        if valid, else return as-is."""
        if not value:
            return value
        try:
            return safe_eval(value, globals_dict=self._get_payload_globals_dict())
        except SyntaxError:
            return value

    def get_login(self, api_data, ssl_context):
        """
        Handle authentication for REST and XMLRPC
            - XMLRPC will return token is `uid`
            - REST will return token is `session`
        """
        api_data.ensure_one()

        if api_data.api_type == "rest_api":
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": api_data.auth_db,
                    "login": api_data.auth_username,
                    "password": api_data.auth_password,
                },
            }
            response = requests.post(
                f"{self._eval_config_value(api_data.endpoint_url)}/web/session/authenticate",
                json=payload,
                timeout=10,
                verify=not api_data.disable_ssl,
            )
            response.raise_for_status()
            token = response.cookies.get("session_id")
            if not token:
                raise ValidationError(
                    self.env._(
                        "Authentication failed: "
                        "Invalid database, username or password."
                    )
                )

        elif api_data.api_type == "xmlrpc":
            common = xmlrpc.client.ServerProxy(
                f"{self._eval_config_value(api_data.endpoint_url)}/xmlrpc/2/common",
                context=ssl_context,
            )
            token = common.authenticate(
                api_data.auth_db, api_data.auth_username, api_data.auth_password, {}
            )
            # Authentication failed.
            if not token:
                raise ValidationError(
                    self.env._(
                        "Authentication failed: "
                        "Invalid database, username or password."
                    )
                )

        else:
            raise ValidationError(
                self.env._("Unsupported API type: %s") % api_data.api_type
            )
        # Update token
        api_data.write({"auth_token": token})
        return token

    # ----------------------------------------------------------
    # XML-RPC
    # ----------------------------------------------------------
    def _execute_xmlrpc_api(self, models, api_data, auth_token, payload=None):
        """auth_token for xmlrpc is uid, It must be interger only"""
        payload = payload or {}
        try:
            json_context = json.loads(api_data.execute_context or "{}")
        except Exception as e:
            raise ValidationError(
                self.env._(f"execute_context is not valid JSON: {e}")
            ) from e

        result = models.execute_kw(
            api_data.auth_db,
            int(auth_token),
            api_data.auth_password,
            api_data.execute_model,
            api_data.execute_method,
            [payload],
            json_context,
        )
        return result

    # ----------------------------------------------------------
    # REST API
    # ----------------------------------------------------------
    def _execute_rest_api(self, api_data, auth_token, payload=None, params=None):
        payload = payload or {}
        headers = safe_eval(
            api_data.headers or "{}",
            globals_dict=self._get_header_globals_dict(auth_token),
        )
        method = (api_data.method or "get").upper()
        if method in ("GET", "DELETE"):
            merged_params = {**(payload or {}), **(params or {})}
            kwargs = {"params": merged_params}
        else:
            if getattr(api_data, "is_form_data", False):
                headers.pop("Content-Type", None)
                # Form data only supports strings;
                # auto-serialize nested dict/list to JSON
                kwargs = {
                    "data": {
                        k: json.dumps(v) if isinstance(v, (dict | list)) else v
                        for k, v in payload.items()
                    }
                }
            else:
                kwargs = {"json": payload}
            if params:
                kwargs["params"] = params
        try:
            url = (
                f"{self._eval_config_value(api_data.endpoint_url)}{api_data.route_path}"
            )
            result = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs,
            )
            result.raise_for_status()
            return result
        except (requests.Timeout, requests.ConnectionError) as e:
            raise ValidationError(self.env._("Connection error: %s") % e) from e
        except requests.HTTPError as e:
            raise ValidationError(self.env._("HTTP error: %s") % e) from e

    def _connect_odoo(self, api_data, auth_token, payload, ssl_context, params=None):
        if api_data.api_type == "xmlrpc":
            route = api_data.route_path or "/xmlrpc/2/object"
            models = xmlrpc.client.ServerProxy(
                f"{self._eval_config_value(api_data.endpoint_url)}{route}",
                context=ssl_context,
            )
            try:
                raw = self._execute_xmlrpc_api(models, api_data, auth_token, payload)
            except Exception as e:
                if "Access Denied" in str(e) and api_data.auth_method != "static_token":
                    auth_token = self.get_login(api_data, ssl_context)
                    raw = self._execute_xmlrpc_api(
                        models, api_data, auth_token, payload
                    )
                else:
                    _logger.exception("_connect_odoo with XML-RPC Error")
                    return {"is_success": False, "message": str(e)}
            # Wrap raw xmlrpc result so _is_result_success can use
            # default "is_success" key egardless of what execute_kw
            # returned ([], True, int, list, dict, etc.)
            return {"is_success": True, "result": raw}

        # Rest API
        try:
            result = self._execute_rest_api(
                api_data, auth_token, payload, params=params
            )
            data = result.json()
        except Exception as e:
            _logger.exception("_connect_odoo with Rest API Error")
            return {"is_success": False, "message": str(e)}

        # Retry on session expired
        if (
            isinstance(data, dict)
            and data.get("error", {}).get("message") == "Odoo Session Expired"
            and api_data.auth_method != "static_token"
        ):
            auth_token = self.get_login(api_data, ssl_context)
            response = self._execute_rest_api(
                api_data, auth_token, payload, params=params
            )
            data = response.json()
        return data

    def _connect_external(self, api_data, auth_token, payload, params=None):
        """Handle generic external REST APIs (Other systems)."""
        try:
            response = self._execute_rest_api(
                api_data, auth_token, payload, params=params
            )
            return response.json()
        except Exception as e:
            _logger.exception("_connect_external Error")
            return {"is_success": False, "message": str(e)}

    def _connect_system(self, api_data, auth_token, payload, ssl_context, params=None):
        if api_data.endpoint_system == "external":
            return self._connect_external(api_data, auth_token, payload, params=params)
        return {"is_success": False, "message": "Not Implemented yet."}

    def _execute_api_request(
        self, api_data, auth_token, payload, ssl_context, params=None
    ):
        if api_data.endpoint_system == "odoo":
            return self._connect_odoo(
                api_data, auth_token, payload, ssl_context, params=params
            )
        return self._connect_system(
            api_data, auth_token, payload, ssl_context, params=params
        )

    def _get_data_payload_callback(self, result):
        """NOTE: Implement data dict callback here"""
        return {"status": "success", "result": result}

    def _handle_callback(self, api_data, result):
        """Send callback to external system if configured."""
        if not api_data.callback_url:
            return

        try:
            payload = self._get_data_payload_callback(result)
            requests.post(
                self._eval_config_value(api_data.callback_url), json=payload, timeout=10
            )
            self.write({"callback_status": "success"})
        except Exception:
            _logger.exception("Callback URL failed")
            self.write({"callback_status": "failed"})

    def _hook_update_data(self, code_api, result):
        """
        Hook called after a successful API call. Override to write result data
        back to local records.

        The shape of ``result`` depends on the API type:

        - **REST API**: the full parsed JSON response from the external system.
          e.g. ``{"is_success": True, "data": {...}}``

        - **XML-RPC**: always wrapped as ``{"is_success": True, "result": <raw>}``
          where ``<raw>`` is whatever ``execute_kw`` returned
          (list of dicts, integer id, True, empty list, etc.)
          Access the actual data via ``result.get("result")``.

        Example override::

            def _hook_update_data(self, code_api, result):
                if code_api == "MY_XMLRPC_API":
                    records = result.get("result", [])
                    self.write({"synced_count": len(records)})
                elif code_api == "MY_REST_API":
                    self.write({"external_id": result.get("id")})
        """
        return

    def _get_result_config(self, api_data):
        """Return (success_key, success_value, message_key) from api_data config."""
        success_key = "is_success"
        success_value = False
        message_key = "message"
        if api_data:
            success_key = api_data.result_success_key
            success_value = api_data.result_success_value
            message_key = api_data.result_message_key
        return success_key, success_value, message_key

    def _get_nested_value(self, result, key_path):
        """
        Traverse result using dot-notation key_path.
        Supports dict keys and list indices.
            e.g. "result.is_success"  - result["result"]["is_success"]
                 "0.status"           - result[0]["status"]
                 "data.items.0.code"  - result["data"]["items"][0]["code"]
        Returns (found: bool, value).
        """
        current = result
        for key in key_path.split("."):
            if isinstance(current, dict):
                if key not in current:
                    return False, None
                current = current[key]
            elif isinstance(current, list):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError):
                    return False, None
            else:
                return False, None
        return True, current

    def _is_result_success(self, result, success_key, success_value):
        """
        Evaluate whether result indicates success. Handles multiple response shapes:

        - Primitive (bool/int/str):
            truthy check, or compare str(value) == success_value if set.
        - dict:
            resolve value via dot-notation success_key, then apply same compare logic.
        - list:
            if success_key is set, resolve from first element (index 0).
            if success_key is empty, non-empty list = success.
        - Nested structures are accessed via dot-notation key path.
        """
        # Primitive types (bool, int, str, None)
        if not isinstance(result, (dict | list)):
            if success_value:
                return str(result) == success_value
            return bool(result)

        # No key configured - treat non-empty collection as success
        if not success_key:
            return bool(result)

        found, raw_val = self._get_nested_value(result, success_key)
        if not found:
            # Key not found - fall back to non-empty check
            return bool(result)

        if success_value:
            return str(raw_val) == success_value
        return bool(raw_val)

    def _action_update_result(self, api_data, result, payload):
        """
        This method for check result, each system will return result is not same.
        So, this method can hook to check result message and do something.

        Returns:
            tuple(bool, str):
                - success flag (True/False)
                - error message (non-empty if failed)
        """
        success_key, success_value, message_key = self._get_result_config(api_data)
        is_success = self._is_result_success(result, success_key, success_value)
        error_msg = ""
        if not is_success and isinstance(result, (dict | list)):
            _, error_msg = self._get_nested_value(result, message_key)
            error_msg = error_msg or ""

        # Save log if needed
        if api_data and api_data.save_log:
            self._create_api_log(
                api_data=api_data,
                payload=payload,
                state="success" if is_success else "failed",
                result=result,
                error_message=error_msg,
            )
        if not is_success:
            return 0, error_msg
        return 1, ""

    def action_call_api(self, code_api):
        api_data = None
        payload = None
        try:
            api_data = self.env["api.config"].search([("code", "=", code_api)])
            if not api_data:
                raise ValidationError(
                    self.env._("API config not found for code: %s") % code_api
                )

            auth_token = False
            ssl_context = None
            if api_data.disable_ssl:
                ssl_context = ssl._create_unverified_context()

            if api_data.auth_required:
                if api_data.auth_method == "static_token":
                    auth_token = self._eval_config_value(api_data.auth_token)
                    if not auth_token:
                        raise ValidationError(
                            self.env._("Static token is required but not set.")
                        )
                else:
                    auth_token = api_data.auth_token or self.get_login(
                        api_data, ssl_context
                    )
                    if not auth_token:
                        raise ValidationError(
                            self.env._("No valid authentication token.")
                        )

            try:
                payload = safe_eval(
                    api_data.python_code or "{}",
                    globals_dict=self._get_payload_globals_dict(),
                )
            except Exception as e:
                raise ValidationError(
                    self.env._(
                        "Invalid Python expression in 'JSON / Payload' field.\n\n"
                        "Error: %s"
                    )
                    % e
                ) from e
            params = None
            if api_data.params_code:
                try:
                    params = safe_eval(
                        api_data.params_code,
                        globals_dict=self._get_payload_globals_dict(),
                    )
                except Exception as e:
                    raise ValidationError(
                        self.env._(
                            "Invalid Python expression in 'Params' field.\n\n"
                            "Error: %s"
                        )
                        % e
                    ) from e
            result = self._execute_api_request(
                api_data, auth_token, payload, ssl_context, params=params
            )

            # Not success
            is_success, message_err = self._action_update_result(
                api_data, result, payload
            )
            if not is_success:
                self._write_failed_state(message_err)
                self._hook_on_failed(code_api, message_err)
                return self._notify_user("danger", message_err)

            # Success
            self.write(
                {
                    "api_status": "success",
                    "api_result": self._truncate_text(result),
                }
            )
            self._hook_update_data(code_api, result)
            self._handle_callback(api_data, result)
            return self._notify_user("success", self.env._("API call successful."))

        except Exception as e:
            _logger.exception("Call API Error")
            self._create_api_log(
                api_data=api_data,
                payload=payload,
                state="failed",
                result=str(e),
            )
            self._write_failed_state(str(e))
            self._hook_on_failed(code_api, str(e))
            return self._notify_user("danger", str(e))

    def _create_api_log(
        self,
        api_data,
        payload,
        state,
        result=None,
        error_message=None,
    ):
        """Create an API call log record."""
        log_model = self.env["api.connector.log"].sudo()
        res_id = self.id if self._name != "api.connector.log" else 0
        log_model.create(
            {
                "api_code": api_data.code if api_data else "N/A",
                "api_name": api_data.name if api_data else "N/A",
                "end_point": api_data.endpoint_system if api_data else "N/A",
                "res_model": self._name,
                "res_id": res_id,
                "state": state,
                "payload": self._truncate_text(str(payload))
                if payload is not None
                else False,
                "result": self._truncate_text(str(result))
                if result is not None
                else False,
                "error_message": error_message,
            }
        )
