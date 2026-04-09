# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import ast
import logging
import re

from odoo import api, models, tools
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WebhookUtils(models.AbstractModel):
    _name = "webhook.utils"
    _description = "Utils Class"

    @tools.ormcache("model", "key_search", "val", "extra_domain")
    def _call_field_search_cache(self, model, key_search, val, extra_domain="[]"):
        """Search records by an explicit field name.
        All args must be hashable strings for ORM cache compatibility."""
        val = ast.literal_eval(val)
        domain = [(key_search, "in", val)] + ast.literal_eval(extra_domain)
        return model.search(domain)

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

    def _create_file_attachment(self, objs, data_dict, line_all_fields):
        Attachment = self.env["ir.attachment"]

        def add_attachments(obj, data_dict, file_attach):
            file_attach += self._get_dict_attachment(
                data_dict.get("attachment_ids", []), obj._name, obj.id
            )
            for line_field, line_data in data_dict.items():
                if isinstance(line_data, list) and line_field in obj:
                    for i, obj_line in enumerate(obj[line_field]):
                        line_data_dict = line_data[i]
                        add_attachments(obj_line, line_data_dict, file_attach)

        file_attach = []
        for obj in objs:
            add_attachments(obj, data_dict, file_attach)

        if file_attach:
            Attachment.create(file_attach)

    def process_lines(self, rec, data_dict, auto_create):
        final_line_dict = []
        final_line_append = final_line_dict.append

        for line_data_dict in data_dict:
            line_dict, line_fields = self._get_o2m_line(line_data_dict, rec)
            line_dict = self._finalize_data_to_write(rec, line_dict, auto_create)

            for line_sub_field in line_fields:
                if line_sub_field in line_data_dict:
                    sub_line_dicts = self.process_lines(
                        rec[line_sub_field], line_data_dict[line_sub_field], auto_create
                    )
                    line_dict.update({line_sub_field: sub_line_dicts})

            final_line_append((0, 0, line_dict))

        return final_line_dict

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
            rec_dict[line_field] = self.process_lines(
                rec[line_field], data_dict[line_field], auto_create
            )

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
                # many2one  -> {lookup_field: value}
                'field2_id': {'name': value2},
                # many2one  -> by ID
                'field2_id': {'id': 5},
                # many2many ->
                #   {"mode": "add"|"replace", "records": [{lookup_field: value}]}
                #   mode is optional, defaults to "replace"
                'tag_ids': {
                    'mode': 'replace',
                    'records': [{'name': 'Tag1'}, {'name': 'Tag2'}]
                },
                'tag_ids': {'mode': 'add',     'records': [{'name': 'Tag1'}]},
                'tag_ids': {'records': [{'name': 'Tag1'}]},  # same as replace
                'attachment_ids': [               # attach file(s)
                    {'name': value3, 'datas': value4}
                ],
                'line_ids': [                     # one2many -> list of record dicts
                    {
                        'field3': value5,
                        'field4_id': {'name': value6},  # nested many2one
                        'attachment_ids': [             # attach file in line
                            {'name': value7, 'datas': value8}
                        ],
                    },
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
            "messages": self.env._("Record created successfully"),
        }
        # Clear cache
        self.env.registry.clear_cache()
        return res

    def _search_object(self, model, vals):
        search_key = vals.get("search_key", {})
        # Prepare Header Dict (non o2m)
        if not search_key:
            raise ValidationError(
                self.env._("Parameter 'search_key' in 'vals' not found!")
            )

        search_domain = [
            (k, "in" if isinstance(v, list) else "=", v) for k, v in search_key.items()
        ]

        # search record to update
        return self.env[model].with_context(prefetch_fields=True).search(search_domain)

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
                # many2one  -> {lookup_field: value}
                'field2_id': {'name': value2},
                # many2many ->
                #   {"mode": "add"|"replace", "records": [{lookup_field: value}]}
                #   mode is optional, defaults to "replace"
                'tag_ids': {'mode': 'replace', 'records': [{'name': 'Tag1'}]},
                'tag_ids': {'mode': 'add',     'records': [{'name': 'Tag1'}]},
                # one2many -> list of record dicts
                'line_ids': [
                    {
                        'field3': value3,
                        'field4_id': {'name': value4},
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

        rec = self._search_object(model, vals)

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
            rec_dict[line_field] = self.process_lines(
                rec[line_field], data_dict[line_field], auto_create
            )

        rec.write(rec_dict)

        # Create Attachment (if any)
        self._create_file_attachment(rec, data_dict, line_all_fields)
        res = {
            "is_success": True,
            "result": {"id": rec.ids},
            "messages": self.env._("Record updated successfully"),
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

                    # For case reference type, convert to list
                    if model_obj._fields[key].type == "reference":
                        sub_model = value.split(",")[0]
                        value = [value.split(",")[1]]
                    else:
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
        # Clear caches (use set to avoid redundant clears for repeated models)
        for model in set(model_list):
            self.env[model].env.registry.clear_cache()
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
        result_dict = []
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

    def _get_company_domain(
        self, have_company, model, rec_dict, main_company, ignore_checkcompany_model
    ):
        if have_company and model not in ignore_checkcompany_model:
            company_id = rec_dict.get("company_id", main_company.id)
            return str([("company_id", "=", company_id)])
        return "[]"

    def _do_auto_create(self, Model, key, auto_create):
        new_recs = (
            auto_create[key]
            if isinstance(auto_create[key], list)
            else [auto_create[key]]
        )
        for new_rec in new_recs:
            self.friendly_create_data(Model._name, {"payload": new_rec})

    def _process_many2_field(
        self,
        rec,
        key,
        rec_dict,
        ftype,
        auto_create,
        ignore_checkcompany_model,
        main_company,
    ):
        model = rec._fields[key].comodel_name
        Model = self.env[model]
        val = rec_dict[key]
        # When looking up by id, skip company filtering: the ID is globally unique
        # and Odoo's own record rules will enforce company access if needed.
        lookup_by_id = self._val_lookup_by_id(ftype, val)
        have_company = hasattr(Model, "company_id") and not lookup_by_id
        extra_domain = self._get_company_domain(
            have_company, model, rec_dict, main_company, ignore_checkcompany_model
        )
        if ftype == "many2many":
            return self._process_many2many_field(
                Model, val, extra_domain, key, auto_create
            )
        return self._process_many2one_field(Model, val, extra_domain, key, auto_create)

    def _process_many2one_field(self, Model, val, extra_domain, key, auto_create):
        """Resolve a many2one value to a record ID.

        val must be a dict with exactly one key-value pair specifying the
        lookup field and its value, e.g. ``{"name": "Customer A"}`` or
        ``{"id": 5}``.
        """
        key_search, search_val = next(iter(val.items()))
        records = self._call_field_search_cache(
            Model, key_search, str([search_val]), extra_domain
        )

        if len(records) > 1:
            Model.env.registry.clear_cache()
            raise ValidationError(
                self.env._("'%(val)s' matched more than 1 record") % {"val": search_val}
            )

        if not records and auto_create.get(key):
            self._do_auto_create(Model, key, auto_create)
            records = self._call_field_search_cache(
                Model, key_search, str([search_val]), extra_domain
            )

        if not records:
            Model.env.registry.clear_cache()
            raise ValidationError(
                self.env._("'%(key)s': '%(val)s' found no match.")
                % {"key": key, "val": search_val}
            )

        return records[0].id

    def _process_many2many_field(self, Model, val, extra_domain, key, auto_create):
        """Resolve a many2many value to ORM write commands.

        Format::

            {"mode": "replace", "records": [{"lookup_field": value}, ...]}
            {"mode": "add",     "records": [{"lookup_field": value}, ...]}
            {"records": [...]}  # mode omitted → defaults to "replace"

        ``mode`` is optional, defaults to ``"replace"``. Each record item must
        contain exactly one key-value pair specifying the lookup field and its value.
        """
        mode = val.get("mode", "replace")
        if mode not in ("add", "replace"):
            raise ValidationError(
                self.env._(
                    "many2many field '%(key)s': 'mode' must be 'add' or 'replace'"
                )
                % {"key": key}
            )
        records_list = val.get("records", [])

        # Group items by lookup field to batch DB queries per group.
        # e.g. [{"name": "T1"}, {"name": "T2"}, {"ref": "R1"}]
        # -> {"name": ["T1", "T2"], "ref": ["R1"]} -> 2 queries instead of 3
        groups: dict[str, list] = {}
        for item in records_list:
            key_search, search_val = next(iter(item.items()))
            groups.setdefault(key_search, []).append(search_val)

        all_records = Model.browse()
        for key_search, search_vals in groups.items():
            records = self._call_field_search_cache(
                Model, key_search, str(search_vals), extra_domain
            )

            if not records and auto_create.get(key):
                self._do_auto_create(Model, key, auto_create)
                records = self._call_field_search_cache(
                    Model, key_search, str(search_vals), extra_domain
                )

            if not records:
                Model.env.registry.clear_cache()
                raise ValidationError(
                    self.env._("'%(key)s': '%(val)s' found no match.")
                    % {"key": key, "val": search_vals}
                )

            all_records |= records

        if mode == "replace":
            return [(6, 0, all_records.ids)]
        return [(4, rec.id) for rec in all_records]

    @api.model
    def _finalize_data_to_write(self, rec, rec_dict, auto_create=False):
        """Resolve relational field values in rec_dict to ORM-ready IDs/commands.

        - many2one  : ``{"lookup_field": value}`` -> integer ID
        - many2many : ``[{"lookup_field": val}, ...]`` -> [(4/6, ...)] commands
        - other fields are passed through unchanged.
        """
        final_dict = {}
        ICP = self.env["ir.config_parameter"]
        ignore_checkcompany_model = ICP.sudo().get_param(
            "webhook.ignore_checkcompany_model", "[]"
        )
        auto_create = auto_create or {}
        main_company = self.env.company
        for key, value in rec_dict.items():
            ffield = rec._fields.get(key, False)
            if ffield:
                ftype = ffield.type
                # For performance, we only check if key in rec_dict and param is not ID
                if self._is_many2_field_with_string(ftype, key, rec_dict):
                    value = self._process_many2_field(
                        rec,
                        key,
                        rec_dict,
                        ftype,
                        auto_create,
                        ignore_checkcompany_model,
                        main_company,
                    )
            final_dict[key] = value
        return final_dict

    def _val_lookup_by_id(self, ftype, val):
        """Return True if val resolves a record purely by database id.

        many2one : ``{"id": 5}``
        many2many: ``[{"id": 1}, {"id": 2}]`` or replace-mode where every
                   record item uses ``"id"`` as the lookup key.
        """
        if ftype == "many2one":
            return isinstance(val, dict) and list(val) == ["id"]
        if ftype == "many2many" and isinstance(val, dict):
            records = val.get("records", [])
            return bool(records) and all(
                isinstance(item, dict) and list(item) == ["id"] for item in records
            )
        return False

    def _is_many2_field_with_string(self, ftype, key, rec_dict):
        if key not in rec_dict or not rec_dict.get(key):
            return False
        val = rec_dict[key]
        # many2one: {"field": "value"} or {"id": 5}
        if ftype == "many2one" and isinstance(val, dict):
            return True
        # many2many: {"mode": "add"|"replace", "records": [...]}
        if ftype == "many2many" and isinstance(val, dict):
            return True
        return False

    @api.model
    def create_data(self, model, vals):
        _logger.info(f"[{model}].create_data(), input: {vals}")
        res = self.friendly_create_data(model, vals)
        if res["is_success"]:
            res_id = res["result"]["id"]
            p = self.env[model].browse(res_id)
            result_field = vals.get("result_field", [])
            for result in result_field:
                res["result"][result] = p[result]
        _logger.info(f"[{model}].create_data(), output: {res}")
        return res

    @api.model
    def update_data(self, model, vals):
        _logger.info(f"[{model}].update_data(), input: {vals}")
        res = self.friendly_update_data(model, vals)
        if res["is_success"]:
            search_key = vals.get("search_key", {})
            for key, value in search_key.items():
                res["result"][key] = value
        _logger.info(f"[{model}].update_data(), output: {res}")
        return res

    @api.model
    def create_update_data(self, model, vals):
        _logger.info(f"[{model}].create_update_data(), input: {vals}")
        # Update
        rec = self._search_object(model, vals)
        if not rec:
            return self.create_data(model, vals)  # fall back to create
        res = self.friendly_update_data(model, vals)
        if res["is_success"]:
            search_key = vals.get("search_key", {})
            for key, value in search_key.items():
                res["result"][key] = value
        _logger.info(f"[{model}].create_update_data(), output: {res}")
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
            - For many2one, one2many and many2many fields,
                you can specify the fields to fetch by using the following format:
                `["<field_name1>", "<field_name2>{<field_name3>, <field_name4>}"]`
                where `<field_name1>` and `<field_name2>` are fields from the model,
                and `<field_name3>` and `<field_name4>` are fields
                from the related model.
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
        _logger.info(f"[{model}].search_data(), input: {vals}")
        result = self._common_search_data(model, vals)
        res = {
            "is_success": True,
            "result": result,
            "messages": self.env._("Record search successfully"),
        }
        _logger.info(f"[{model}].search_data(), output: {res}")
        return res

    @api.model
    def call_function(self, model, vals):
        """
        Call a method on a specific model record using the provided input.

        This method allows you to dynamically call a function on a model object
        with optional parameters and context.

        Parameters
        ----------
        model : str
            The name of the model to call the function on.
        vals : dict
            A dictionary containing the following keys:
                - search_key : dict
                    Criteria used to search for the target record.
                - payload : dict
                    - method (str): The name of the method to call on the record.
                    - parameter (dict, optional):
                        Keyword arguments to pass to the method.
                    - context (dict, optional): Context to use when calling the method.

        Returns
        -------
        dict
            A dictionary containing:
                - is_success (bool): True if the method call succeeded.
                - result (any): The return value of the called method.
                - messages (str): Status message.

        Example
        -------
        {
            "params": {
                "model": "account.move",
                "vals": {
                    "search_key": {"name": "INV/2021/0001"},
                    "payload": {
                        "method": "action_post",
                        "parameter": {},
                        "context": {"force_create": True},
                    }
                }
            }
        }
        """
        _logger.info("[%s].call_function(), input: %s", model, vals)

        data_dict = vals.get("payload", {})
        method_name = data_dict.get("method")
        parameter = data_dict.get("parameter", {})
        context = data_dict.get("context", {})

        if not method_name:
            raise ValidationError(self.env._("Missing 'method' in payload"))

        rec = self._search_object(model, vals).with_context(**context)

        if not hasattr(rec, method_name):
            raise AttributeError(
                f"Record(s) of model {model} has no method '{method_name}'"
            )

        result = getattr(rec, method_name)(**(parameter or {}))
        return {
            "is_success": True,
            "result": result,
            "messages": f"Function '{method_name}' called successfully",
        }
