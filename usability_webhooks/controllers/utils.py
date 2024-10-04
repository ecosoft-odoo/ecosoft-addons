# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import ast
import logging
import re

from odoo import _, api, models, tools
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WebhookUtils(models.AbstractModel):
    _name = "webhook.utils"
    _description = "Utils Class"

    @tools.ormcache("model", "val")
    def _call_name_search_cache(self, model, val, args=None):
        args = args or []
        return model.name_search(val, args=args, operator="=")

    @tools.ormcache("model", "val")
    def _call_search_cache(self, model, val):
        return model.search([("id", "=", val)])

    def _get_o2m_line(self, line_data_dict, line_obj):
        rec_fields = []
        rec_fields_append = rec_fields.append
        line_fields = []
        for field, model_field in line_obj._fields.items():
            if field in line_data_dict and model_field.type != "one2many":
                rec_fields_append(field)
            elif field in line_data_dict:
                line_fields.append(field)
        line_dict = {k: v for k, v in line_data_dict.items() if k in rec_fields}
        return line_dict, line_fields

    def _get_dict_attachment(self, list_attachment, model, res_id):
        return [
            {
                "name": attach["name"],
                "res_model": model,
                "res_id": res_id,
                "datas": attach["datas"].encode("ascii"),
            }
            for attach in list_attachment
        ]

    def _create_file_attachment(self, obj, data_dict, line_all_fields):
        Attachment = self.env["ir.attachment"]
        file_attach = self._get_dict_attachment(
            data_dict.get("attachment_ids", []), obj._name, obj.id
        )
        for line_field in line_all_fields:
            # Add attachment on o2m level 1
            for i, obj_line in enumerate(obj[line_field]):
                line_data_dict = data_dict[line_field][i]
                file_attach += self._get_dict_attachment(
                    line_data_dict.get("attachment_ids", []),
                    obj_line._name,
                    obj_line.id,
                )
                # Find sub line in line
                line_fields = self._get_o2m_line(line_data_dict, obj_line)[1]
                for line_sub_field in line_fields:
                    # Add attachment on o2m level 2
                    for j, obj_sub_line in enumerate(obj_line[line_sub_field]):
                        sub_line_data_dict = line_data_dict[line_sub_field][j]
                        file_attach += self._get_dict_attachment(
                            sub_line_data_dict.get("attachment_ids", []),
                            obj_sub_line._name,
                            obj_sub_line.id,
                        )
        if file_attach:
            Attachment.create(file_attach)

    def _convert_data_to_id(self, model, vals):
        data_dict = vals.get("payload", {})
        auto_create = vals.get("auto_create", {})
        rec = self.env[model].new()  # Dummy record
        rec_fields = []
        line_all_fields = []
        for field, model_field in rec._fields.items():
            if field in data_dict and model_field.type != "one2many":
                rec_fields.append(field)
            elif field in data_dict:
                line_all_fields.append(field)
        rec_dict = {k: v for k, v in data_dict.items() if k in rec_fields}
        rec_dict = self._finalize_data_to_write(rec, rec_dict, auto_create)
        # Prepare Line Dict (o2m)
        for line_field in line_all_fields:
            final_line_dict = []
            final_line_append = final_line_dict.append
            # Loop all o2m lines, and recreate it
            for line_data_dict in data_dict[line_field]:
                line_dict, line_fields = self._get_o2m_line(
                    line_data_dict, rec[line_field]
                )
                line_dict = self._finalize_data_to_write(
                    rec[line_field], line_dict, auto_create
                )
                # Prepare Sub Line Dict (o2m)
                for line_sub_field in line_fields:
                    final_sub_line_dict = []
                    final_sub_line_append = final_sub_line_dict.append

                    # Loop all o2m sub lines, and recreate it
                    for line_sub_data_dict in line_data_dict[line_sub_field]:
                        # Add company_id if not present
                        if (
                            "company_id" not in line_data_dict
                            and "company_id" in data_dict
                        ):
                            line_data_dict["company_id"] = data_dict["company_id"]
                        sub_line_dict, line_sub_fields = self._get_o2m_line(
                            line_sub_data_dict, rec[line_field][line_sub_field]
                        )
                        sub_line_dict = self._finalize_data_to_write(
                            rec[line_field][line_sub_field], sub_line_dict, auto_create
                        )
                        final_sub_line_append((0, 0, sub_line_dict))
                        if line_sub_fields:
                            rec.clear_caches()
                            raise ValidationError(
                                _(
                                    "friendly_create_data() support "
                                    "2 level of one2many lines"
                                )
                            )
                    line_dict.update({line_sub_field: final_sub_line_dict})
                final_line_append((0, 0, line_dict))
            rec_dict[line_field] = final_line_dict
        return rec_dict, rec, line_all_fields

    @api.model
    def friendly_create_data(self, model, vals):
        """Accept friendly data_dict in following format to create data,
            and auto_create data if found no match.
        -------------------------------------------------------------
        vals:
        {
            'payload': {
                'field1': value1,
                'field2_id': value2,  # can be ID or name search string
                'attachment_ids': [  # for attach file
                    {
                        'name': value3,
                        'datas': value4,
                    }
                ]
                'line_ids': [
                    {
                        'field3': value5,
                        'field4_id': value6,  # can be ID or name search string
                    },
                    'attachment_ids': [  # for attach file in line
                        {
                            'name': value7,
                            'datas': value8,
                        }
                    ],
                    {..new record..}, {..new record..}, ...
                ],
            },
            'auto_create': {
                'field2_id': {'name': 'some name', ...},
                'field4_id': {'name': 'some name', ...},
                # If more than 1 value, you can use list instead
                # 'field4_id': [{'name': 'some name', ...}, {...}, {...}]
            }
        }
        """
        data_dict = vals.get("payload", {})
        rec_dict, rec, line_all_fields = self._convert_data_to_id(model, vals)
        company_id = rec_dict.get("company_id") or self.env.company.id
        # Send context to function create()
        obj = rec.with_context(
            api_payload=data_dict, default_company_id=company_id
        ).create(rec_dict)
        # Create Attachment (if any)
        self._create_file_attachment(obj, data_dict, line_all_fields)
        res = {
            "is_success": True,
            "result": {"id": obj.id},
            "messages": _("Record created successfully"),
        }
        # Clear cache
        rec.clear_caches()
        return res

    def _search_object(self, model, vals):
        search_key = vals.get("search_key", {})
        search_domain = [
            (k, "in" if isinstance(v, list) else "=", v) for k, v in search_key.items()
        ]

        # Prepare Header Dict (non o2m)
        if not search_key:
            raise ValidationError(_("Parameter 'search_key' in 'vals' not found!"))

        # search record to update
        rec = self.env[model].search(search_domain)
        return rec

    @api.model
    def friendly_update_data(self, model, vals):
        """Accept friendly data_dict in following format to update existing rec
        This method, will always delete o2m lines and recreate it.
        -------------------------------------------------------------
        vals:
        {
            'search_key': {
                "<key_field>": "<key_value>",
            },
            'payload': {
                'field1': value1,
                'field2_id': value2,  # can be ID or name search string
                'line_ids': [
                    {
                        'field3': value3,
                        'field4_id': value4,  # can be ID or name search string
                    },
                    {..new record..}, {..new record..}, ...
                ],
            }
            'auto_create': {
                'field2_id': {'name': 'some name', ...},
                'field4_id': {'name': 'some name', ...},
                # If more than 1 value, you can use list instead
                # 'field4_id': [{'name': 'some name', ...}, {...}, {...}]
            }
        },
        """
        data_dict = vals.get("payload", {})
        auto_create = vals.get("auto_create", {})
        search_key = vals.get("search_key", {})

        rec = self._search_object(model, vals)

        if len(rec) > 1:
            raise ValidationError(
                _(
                    "Search key '%(key_field)s' in model '%(model)s' found mutiple matches!"
                )
                % {"key_field": search_key, "model": model}
            )

        rec_fields = []
        line_all_fields = []

        for field, model_field in rec._fields.items():
            if field in data_dict and model_field.type != "one2many":
                rec_fields.append(field)
            elif field in data_dict:
                line_all_fields.append(field)
        rec_dict = {k: v for k, v in data_dict.items() if k in rec_fields}
        rec_dict = self._finalize_data_to_write(rec, rec_dict, auto_create)
        # Prepare Line Dict (o2m)
        for line_field in line_all_fields:
            lines = rec[line_field]
            # First, delete all lines o2m
            lines.unlink()
            final_line_dict = []
            final_line_append = final_line_dict.append
            # Loop all o2m lines, and recreate it
            for line_data_dict in data_dict[line_field]:
                line_dict, line_fields = self._get_o2m_line(
                    line_data_dict, rec[line_field]
                )
                line_dict = self._finalize_data_to_write(
                    rec[line_field], line_dict, auto_create
                )
                # Prepare Sub Line Dict (o2m)
                for line_sub_field in line_fields:
                    final_sub_line_dict = []
                    final_sub_line_append = final_sub_line_dict.append
                    # Loop all o2m sub lines, and recreate it
                    for line_sub_data_dict in line_data_dict[line_sub_field]:
                        sub_line_dict, line_sub_fields = self._get_o2m_line(
                            line_sub_data_dict, rec[line_field][line_sub_field]
                        )
                        sub_line_dict = self._finalize_data_to_write(
                            rec[line_field][line_sub_field], sub_line_dict, auto_create
                        )
                        final_sub_line_append((0, 0, sub_line_dict))
                        if line_sub_fields:
                            rec.clear_caches()
                            raise ValidationError(
                                _(
                                    "friendly_update_data() support "
                                    "2 level of one2many lines"
                                )
                            )
                    line_dict.update({line_sub_field: final_sub_line_dict})
                final_line_append((0, 0, line_dict))
            rec_dict[line_field] = final_line_dict
        rec.write(rec_dict)
        # Create Attachment (if any)
        self._create_file_attachment(rec, data_dict, line_all_fields)
        res = {
            "is_success": True,
            "result": {"id": rec.id},
            "messages": _("Record updated successfully"),
        }
        return res

    def _update_child_2many(self, value, field_2many, sub_model):
        search_domain = [("id", "in", value)]
        return self.env[sub_model].search_read(search_domain, field_2many)

    @tools.ormcache("key", "model_obj")
    def _get_sub_model(self, key, model_obj):
        sub_model = model_obj._fields[key].comodel_name
        return sub_model

    def _update_result_with_2many(self, result, result_dict, model_obj):
        model_list = []
        for res in result:
            for key, value in res.items():
                field_2many = result_dict.get(key)
                # Search values that need to be displayed in the result
                if field_2many:
                    # For case many2one, convert to list
                    if isinstance(value, tuple):
                        value = [value[0]]

                    sub_model = self._get_sub_model(key, model_obj)
                    # Recusive search for 2many fields
                    filtered_values = [x for x in field_2many if "{" in x]
                    sub_result = []
                    if filtered_values:
                        # Update search_field without {}
                        field_2many = [x.split("{")[0] for x in field_2many]
                        sub_result = self._search_subfield(filtered_values)

                    child_result = self._update_child_2many(
                        value, field_2many, sub_model
                    )

                    if filtered_values:
                        child_result = self._update_result_with_2many(
                            child_result, sub_result, self.env[sub_model]
                        )
                    # Replace value with child result
                    res[key] = child_result
                    model_list.append(sub_model)
        # Clear caches
        for model in model_list:
            self.env[model].clear_caches()
        return result

    def _search_subfield(self, filtered_values):
        result_dict = {}
        # Regular expression pattern to match 'field_name{value1, value2}'
        pattern = r"([\w.-]+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        # Iterate over each item in the list
        for item in filtered_values:
            # Use re.match to find matches according to the pattern
            match = re.match(pattern, item)
            if match:
                # Extract the field name and the values inside the curly braces
                field_name, values_str = match.groups()
                # Regular expression to match the desired pattern
                matches = re.findall(r"[^,]+{[^}]+}|[^,]+", values_str)
                # Stripping any leading/trailing spaces from the elements
                values_list = [match.strip() for match in matches]
                # Assign to the result dictionary
                result_dict[field_name] = values_list
        return result_dict

    def _common_search_data(self, model, vals):
        """
        Search and read data from the specified model based on the provided values.

        Args:
            model (str): The name of the model to search data from.
            vals (dict): A dictionary containing the payload data.

        Returns:
            list: A list of records matching the search criteria.

        """
        data_dict = vals.get("payload", {})
        limit = data_dict.get("limit", None)
        order = data_dict.get("order", None)
        # Search all fields if not specified
        search_field = []
        search_domain = []
        if data_dict.get("search_field"):
            search_field = data_dict["search_field"]
            # Filter value with {}
            filtered_values = [x for x in search_field if "{" in x]
            # Update search_field without {}
            search_field = [x.split("{")[0] for x in search_field]
            # search sub field 'field_name{value1, value2}'
            result_dict = self._search_subfield(filtered_values)

        if data_dict.get("search_domain"):
            search_domain = ast.literal_eval(data_dict["search_domain"])

        model_obj = self.env[model]
        result = model_obj.search_read(
            search_domain, search_field, limit=limit, order=order
        )
        # Update result with 2many fields
        if result_dict:
            result = self._update_result_with_2many(result, result_dict, model_obj)

        return result

    @api.model
    def _finalize_data_to_write(self, rec, rec_dict, auto_create=False):
        """For many2one, many2many, use name search to get id"""
        final_dict = {}
        ICP = self.env["ir.config_parameter"]
        ignore_checkcompany_model = ICP.sudo().get_param(
            "webhook.ignore_checkcompany_model"
        )
        auto_create = auto_create or {}
        main_company = self.env.company
        for key, value in rec_dict.items():
            ffield = rec._fields.get(key, False)
            if ffield:
                ftype = ffield.type
                if self._is_many2_field_with_string(ftype, key, rec_dict):
                    model = rec._fields[key].comodel_name
                    Model = self.env[model]
                    search_vals = (
                        ftype == "many2one"
                        and [rec_dict[key]]
                        or rec_dict[key].split(",")
                    )
                    value = []  # for many2many, result will be tuple
                    have_company = hasattr(Model, "company_id")
                    for val in search_vals:
                        # Support multi company
                        args = []
                        if have_company and model not in ignore_checkcompany_model:
                            args = [
                                (
                                    "company_id",
                                    "=",
                                    rec_dict.get("company_id", main_company.id),
                                )
                            ]
                        values = self._call_name_search_cache(Model, val, args)
                        # If failed, try again by ID
                        if len(values) != 1 and val and isinstance(val, int):
                            rec = self._call_search_cache(Model, val)
                            values = len(rec) == 1 and [(rec.id,)] or values
                        # Found > 1, can't continue
                        if len(values) > 1:
                            Model.clear_caches()
                            raise ValidationError(
                                _("'%(val)s' matched more than 1 record") % {"val": val}
                            )
                        # If not found, but auto_create it
                        if len(values) != 1 and auto_create.get(key):
                            new_recs = (
                                auto_create[key]
                                if isinstance(auto_create[key], list)
                                else [auto_create[key]]
                            )
                            for new_rec in new_recs:
                                self.friendly_create_data(model, {"payload": new_rec})
                            values = self._call_name_search_cache(Model, val, args)
                        elif not values:
                            Model.clear_caches()
                            raise ValidationError(
                                _("'%(key)s': '%(val)s' found no match.")
                                % {"key": key, "val": val}
                            )
                        if ftype == "many2one":
                            value = values[0][0]
                        elif ftype == "many2many":
                            value.append((4, values[0][0]))
            final_dict.update({key: value})
        return final_dict

    def _is_many2_field_with_string(self, ftype, key, rec_dict):
        return (
            key in rec_dict.keys()
            and ftype in ("many2one", "many2many")
            and rec_dict[key]
            and isinstance(rec_dict[key], str)
        )

    @api.model
    def create_data(self, model, vals):
        _logger.info("[{}].create_data(), input: {}".format(model, vals))
        res = self.friendly_create_data(model, vals)
        if res["is_success"]:
            res_id = res["result"]["id"]
            p = self.env[model].browse(res_id)
            result_field = vals.get("result_field", [])
            for result in result_field:
                res["result"][result] = p[result]
        _logger.info("[{}].create_data(), output: {}".format(model, res))
        return res

    @api.model
    def update_data(self, model, vals):
        _logger.info("[{}].update_data(), input: {}".format(model, vals))
        res = self.friendly_update_data(model, vals)
        if res["is_success"]:
            search_key = vals.get("search_key", {})
            for key, value in search_key.items():
                res["result"][key] = value
        _logger.info("[{}].update_data(), output: {}".format(model, res))
        return res

    @api.model
    def create_update_data(self, model, vals):
        _logger.info("[{}].create_update_data(), input: {}".format(model, vals))
        # Update
        rec = self._search_object(model, vals)
        if not rec:
            return self.create_data(model, vals)  # fall back to create
        res = self.friendly_update_data(model, vals)
        if res["is_success"]:
            search_key = vals.get("search_key", {})
            for key, value in search_key.items():
                res["result"][key] = value
        _logger.info("[{}].create_update_data(), output: {}".format(model, res))
        return res

    @api.model
    def search_data(self, model, vals):
        """
        ==================================
        Search Data Description
        ==================================
        This utility function facilitates querying records from a specified model
        with customizable search criteria.
        The search parameters include fields to fetch, filtering conditions,
        record limits, and sorting orders.

        Parameters:
        - search_field:
            - Use an empty list `[]` to retrieve all fields from the model.
            - Specify a list of field names `["<field_name1>", "<field_name2>"]`
                to retrieve only those fields.
            - For many2one, one2many and many2many fields, you can specify the fields to fetch
                by using the following format:
                `["<field_name1>", "<field_name2>{<field_name3>, <field_name4>}"]`
                where `<field_name1>` and `<field_name2>` are fields from the model,
                and `<field_name3>` and `<field_name4>` are fields from the related model.
                The related fields will be fetched and displayed in the result.

        - search_domain:
            - Use an empty string `""` to apply no filtering conditions
                (equivalent to fetching all records).
            - Provide a string representation of a list of tuples
                `"[('<field_name>', '<operation>', '<value>')]"`
                to define filtering conditions. Each tuple should contain a field name,
                an operator (e.g., '=', '>', '<'), and the value to compare against.

        - limit:
            - Omit this parameter or set it to `None`
                to fetch all matching records without any limit.
            - Specify an integer to limit the number of records returned.

        - order:
            - Omit this parameter or set it to `None`
                to fetch all matching records any specific ordering.
            - Provide a strings
                `"<field_name1> asc|desc, <field_name2> asc|desc"`
                to sort the results. Each string should specify a field name followed
                by the sorting direction (`asc` for ascending, `desc` for descending).

        ==================================
        Example Format for Search Data:
        ==================================
        {
            "params": {
                "model": "account.move",  # Model to search
                "vals": {
                    "payload": {
                        "search_field": [
                            "name", "date",
                            "invoice_line_ids{product_id, name, account_id}"
                        ],
                        "search_domain": "[('move_type', '=', 'in_invoice')]",
                        "limit": 1,
                        "order": "date desc, name"
                    }
                }
            }
        }
        """
        _logger.info("[{}].search_data(), input: {}".format(model, vals))
        result = self._common_search_data(model, vals)
        res = {
            "is_success": True,
            "result": result,
            "messages": _("Record search successfully"),
        }
        _logger.info("[{}].search_data(), output: {}".format(model, res))
        return res

    @api.model
    def call_function(self, model, vals):
        """
        Call a function on a model object based on the provided input.
        Parameters (search_key) are used to search for the record:
            - search_key: A dictionary containing the search criteria to find the record.

        Parameters (payload) are used to call the function:
            - method (str): The name of the function to call.
            - parameter (dict):
                A dictionary containing the arguments to pass to the function. (if any)

        ==================================
        Example Format for Call Function:
        ==================================
        {
            "params": {
                "model": "account.move",  # Model to call
                "vals": {
                    "search_key": {
                        "name": "INV/2021/0001"
                    },
                    "payload": {
                        "method": "action_post",
                        # Optional, see the function definition for required parameters
                        "parameter": {},
                    }
                }
            }
        }
        """
        _logger.info("[{}].call_function(), input: {}".format(model, vals))
        data_dict = vals.get("payload", {})
        parameter = data_dict.get("parameter", {})

        rec = self._search_object(model, vals)
        res = getattr(rec, data_dict["method"])(**dict(parameter) if parameter else {})
        return {
            "is_success": True,
            "result": res,
            "messages": "Function {} called successfully".format(data_dict["method"]),
        }
