# Copyright 2022 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import ast
import base64
import json
import logging
from collections import defaultdict
from operator import itemgetter

from odoo import Command, api, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.models import get_public_method

_logger = logging.getLogger(__name__)
# Field types whose lookup values compare in Python as in the database
BATCH_TYPES = ("char", "integer", "selection")


def _split_items(text):
    """Split 'a,b{c,d},e' on its top-level commas"""
    items = []
    depth = start = 0
    for i, char in enumerate(text):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise ValueError(text)
        elif char == "," and not depth:
            items.append(text[start:i])
            start = i + 1
    if depth:
        raise ValueError(text)
    items.append(text[start:])
    return [item.strip() for item in items if item.strip()]


def parse_fields_spec(fields_spec):
    """Parse a 'field{sub1,sub2{a,b}}' list, at any depth, into
    [(field name, sub spec)], sub spec being None for a plain field.
    Raise ValueError on unbalanced braces. A field given twice keeps its
    last spec.

    ['name', 'tag_id{name}'] -> [('name', None), ('tag_id', [('name', None)])]
    """
    spec = {}
    for item in fields_spec:
        name, brace, rest = item.partition("{")
        sub_spec = None
        if brace:
            if not rest.endswith("}"):
                raise ValueError(item)
            sub_spec = parse_fields_spec(_split_items(rest[:-1]))
        spec[name.strip()] = sub_spec
    return list(spec.items())


class WebhookUtils(models.AbstractModel):
    _name = "webhook.utils"
    _description = "Utils Class"

    def _with_lookup_memo(self):
        """Give one API call its own lookup memo, like `import_cache` in load().
        Never shared across requests or users, unlike an ormcache."""
        if "webhook_lookup_memo" in self.env.context:
            return self
        return self.with_context(webhook_lookup_memo={})

    def _call_field_search_cache(self, model, domain, company_domain=None):
        """Search ``domain`` within ``company_domain``. Found records are
        memoized for the current API call only."""
        domain = Domain(domain)
        if company_domain is not None:
            domain &= Domain(company_domain)  # overrides may return a list
        memo = self.env.context.get("webhook_lookup_memo")
        memo_key = (model.env.uid, model.env.su, model._name, repr(domain))
        if memo is not None and memo_key in memo:
            return model.browse(memo[memo_key])
        records = model.search(domain)
        # No match is not memoized, auto_create searches again after creating
        if memo is not None and records:
            memo[memo_key] = records.ids
        return records

    def _prepare_write_vals(self, model_obj, data_dict, auto_create, company=None):
        """ORM values of a payload for ``model_obj``: relational lookups are
        resolved, one2many lines become create commands. Keys that are not
        fields of the model are ignored. Lookups are scoped on the payload
        company_id, else on ``company`` (of the parent), else env.company."""
        rec_dict = {}
        line_fields = []
        for key, value in data_dict.items():
            # Files are created by _create_file_attachment, even when the
            # model has an attachment_ids field
            field = key != "attachment_ids" and model_obj._fields.get(key)
            if field and field.type == "one2many":
                line_fields.append(field)
            elif field:
                rec_dict[key] = value
        rec_dict = self._finalize_data_to_write(
            model_obj, rec_dict, auto_create, company
        )
        # Lines are in the company of their parent
        line_company = rec_dict.get("company_id", company)
        for field in line_fields:
            line_model = self.env[field.comodel_name]
            rec_dict[field.name] = [
                Command.create(
                    self._prepare_write_vals(
                        line_model, line, auto_create, line_company
                    )
                )
                for line in data_dict[field.name]
            ]
        return rec_dict

    def _get_dict_attachment(self, list_attachment, model, res_id):
        return [
            {
                "name": attach["name"],
                "res_model": model,
                "res_id": res_id,
                "raw": base64.b64decode(attach["datas"]),
            }
            for attach in list_attachment
        ]

    def _create_file_attachment(self, objs, data_dict):
        """Create the 'attachment_ids' files of the payload on objs, and of
        each one2many line payload on the matching line, recursively"""

        def collect(obj, data_dict):
            files = self._get_dict_attachment(
                data_dict.get("attachment_ids", []), obj._name, obj.id
            )
            for key, lines_data in data_dict.items():
                field = obj._fields.get(key)
                if field and field.type == "one2many":
                    for line, line_data in zip(obj[key], lines_data, strict=False):
                        files += collect(line, line_data)
            return files

        files = [file for obj in objs for file in collect(obj, data_dict)]
        if files:
            self.env["ir.attachment"].create(files)

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
        if "webhook_lookup_memo" not in self.env.context:
            return self._with_lookup_memo().friendly_create_data(model, vals)
        data_dict = vals.get("payload", {})
        Model = self.env[model]
        rec_dict = self._prepare_write_vals(
            Model, data_dict, vals.get("auto_create", {})
        )
        company_id = rec_dict.get("company_id") or self.env.company.id
        # Send context to function create()
        obj = Model.with_context(
            api_payload=data_dict, default_company_id=company_id
        ).create(rec_dict)
        self._create_file_attachment(obj, data_dict)
        res = {
            "is_success": True,
            "result": {"id": obj.id},
            "messages": self.env._("Record created successfully"),
        }
        return res

    def _search_object(self, model, vals):
        search_key = vals.get("search_key", {})
        # Prepare Header Dict (non o2m)
        if not search_key:
            raise ValidationError(
                self.env._("Parameter 'search_key' in 'vals' not found!")
            )

        return self.env[model].search(self._lookup_domain(search_key))

    def _lookup_domain(self, values):
        """Domain of a search_key or of a relational lookup: every key must
        match, a list value matches any of its items"""
        return [(k, "in" if isinstance(v, list) else "=", v) for k, v in values.items()]

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
        if "webhook_lookup_memo" not in self.env.context:
            return self._with_lookup_memo().friendly_update_data(model, vals)
        data_dict = vals.get("payload", {})
        rec = self._search_object(model, vals)
        # One2many lines of the payload replace the existing ones, deleted
        # once every lookup succeeded (auto_create may add new lines)
        old_lines = [
            rec.mapped(key)
            for key in data_dict
            if key in rec._fields and rec._fields[key].type == "one2many"
        ]
        rec_dict = self._prepare_write_vals(rec, data_dict, vals.get("auto_create", {}))
        for lines in old_lines:
            lines.unlink()
        rec.write(rec_dict)
        self._create_file_attachment(rec, data_dict)
        res = {
            "is_success": True,
            "result": {"id": rec.ids},
            "messages": self.env._("Record updated successfully"),
        }
        return res

    def _update_child_2many(self, value, field_2many, sub_model):
        search_domain = [("id", "in", value)]
        return self.env[sub_model].search_read(search_domain, field_2many)

    def _get_2many_ids(self, value, key, model_obj):
        """Return (sub_model, ids) of a relational value given by read()"""
        # For case reference type, "model,id"
        if model_obj._fields[key].type == "reference":
            if not value:
                return False, []
            sub_model, res_id = value.split(",")
            return sub_model, [int(res_id)]
        # For case many2one, (id, display_name)
        if isinstance(value, tuple):
            value = [value[0]]
        return model_obj._fields[key].comodel_name, value or []

    def _expand_subfields(self, rows, spec, model_obj):
        """In rows read from model_obj, replace the value of each 'field{sub}'
        of the parsed spec by the list of its related records, read with
        their sub fields. Related records are read once per field and model,
        for all rows, recursively."""
        for key, sub_spec in spec:
            key_rows = [row for row in rows if key in row]
            # Plain field, or empty spec 'field{}': keep the value as read
            if not sub_spec or not key_rows:
                continue
            row_ids = []
            ids_by_model = defaultdict(set)
            for row in key_rows:
                sub_model, ids = self._get_2many_ids(row[key], key, model_obj)
                row_ids.append((row, sub_model, ids))
                if sub_model:
                    ids_by_model[sub_model].update(ids)
            # {(model, id): (position, child row)}, in the related model order
            children = {}
            for sub_model, ids in ids_by_model.items():
                child_rows = []
                if ids:
                    child_rows = self._update_child_2many(
                        list(ids), [name for name, _sub in sub_spec], sub_model
                    )
                self._expand_subfields(child_rows, sub_spec, self.env[sub_model])
                for position, child in enumerate(child_rows):
                    children[sub_model, child["id"]] = (position, child)
            for row, sub_model, ids in row_ids:
                found = [
                    children[sub_model, i]
                    for i in set(ids)
                    if (sub_model, i) in children
                ]
                row[key] = [child for _pos, child in sorted(found, key=itemgetter(0))]
        return rows

    @api.model
    def _build_records_payload(self, records, fields_spec):
        """Build one payload dict per record using field{sub1,sub2} syntax.
        Same expansion logic as search_data: records are read at once, and
        related records once per relation.

        fields_spec examples:
            ["name", "state"]
            ["name", "currency_id{id,name,code}", "order_line{product_id,qty_done}"]
        Returns dicts with id only when fields_spec is empty.
        """
        if not fields_spec:
            return [{"id": rec_id} for rec_id in records.ids]
        spec = parse_fields_spec(fields_spec)
        rows = records.read([name for name, _sub in spec])
        return self._expand_subfields(rows, spec, records)

    @api.model
    def _build_record_payload(self, rec, fields_spec):
        """Payload dict of a single record, see _build_records_payload"""
        result = self._build_records_payload(rec, fields_spec)
        return result[0] if result else {"id": rec.id}

    @api.model
    def _check_fields_spec(self, model_obj, spec, prefix=""):
        """Return the paths of a parsed field{sub1,sub2} spec that cannot be
        read, e.g. ['country_id.nme'] for 'country_id{nme}'"""
        invalid = []
        for name, sub_spec in spec:
            path = f"{prefix}{name}"
            field = model_obj._fields.get(name)
            if not field:
                invalid.append(path)
            # The model of a reference field is not known in advance
            elif sub_spec is None or field.type == "reference":
                continue
            elif not field.relational:
                invalid.append(self.env._("%s (not relational)", path))
            else:
                sub_model = self.env[field.comodel_name]
                invalid += self._check_fields_spec(sub_model, sub_spec, f"{path}.")
        return invalid

    def _check_result_field(self, model, vals):
        """Error response when vals' result_field cannot be read, checked
        before writing so that nothing is created nor updated"""
        result_field = vals.get("result_field")
        if not result_field:
            return None
        items = result_field if isinstance(result_field, list) else [result_field]
        invalid = []
        for item in items:
            try:
                spec = parse_fields_spec([item]) if isinstance(item, str) else None
            except ValueError:  # unbalanced braces
                spec = None
            if spec is None or not isinstance(result_field, list):
                invalid.append(str(item))
            else:
                invalid += self._check_fields_spec(self.env[model], spec)
        if not invalid:
            return None
        return {
            "is_success": False,
            "messages": self.env._(
                "Invalid result_field, a list of fields is expected: %s",
                ", ".join(invalid),
            ),
        }

    def _add_result_records(self, res, records, vals):
        """Add 'records': the result_field values of each created or updated
        record, read after the write"""
        if res["is_success"] and vals.get("result_field"):
            res["records"] = self._build_records_payload(records, vals["result_field"])
        return res

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
        # All fields when not specified
        spec = parse_fields_spec(data_dict.get("search_field") or [])
        search_domain = ast.literal_eval(data_dict.get("search_domain") or "[]")
        model_obj = self.env[model]
        rows = model_obj.search_read(
            search_domain,
            [name for name, _sub in spec],
            limit=data_dict.get("limit"),
            order=data_dict.get("order"),
        )
        return self._expand_subfields(rows, spec, model_obj)

    def _do_auto_create(self, Model, key, auto_create):
        new_recs = (
            auto_create[key]
            if isinstance(auto_create[key], list)
            else [auto_create[key]]
        )
        for new_rec in new_recs:
            self.friendly_create_data(Model._name, {"payload": new_rec})
        # New records may change any lookup result (e.g. duplicate match)
        self.env.context.get("webhook_lookup_memo", {}).clear()

    def _process_many2_field(self, field, val, company, auto_create):
        Model = self.env[field.comodel_name]
        # The company scope Odoo applies to the field, shared records included:
        # e.g. a tax named 'VAT 7%' in each company is found in ``company`` only
        company_domain = None
        if field.check_company:
            # Properties are checked against the current company
            if field.company_dependent:
                company = self.env.company.id
            company_domain = Model._check_company_domain(company)
        if field.type == "many2many":
            return self._process_many2many_field(
                Model, val, company_domain, field.name, auto_create
            )
        return self._process_many2one_field(
            Model, val, company_domain, field.name, auto_create
        )

    def _process_many2one_field(self, Model, val, company_domain, key, auto_create):
        """Resolve a many2one lookup, e.g. ``{"name": "Customer A"}``, to a
        record ID. See _lookup_ids."""
        return self._lookup_ids(Model, [val], company_domain, key, auto_create)[0]

    def _process_many2many_field(self, Model, val, company_domain, key, auto_create):
        """Resolve a many2many value to ORM write commands.

        Format::

            {"mode": "replace", "records": [{"lookup_field": value}, ...]}
            {"mode": "add",     "records": [{"lookup_field": value}, ...]}
            {"records": [...]}  # mode omitted → defaults to "replace"

        ``mode`` is optional, defaults to ``"replace"``. See _lookup_ids for
        the record items.
        """
        mode = val.get("mode", "replace")
        if mode not in ("add", "replace"):
            raise ValidationError(
                self.env._(
                    "many2many field '%(key)s': 'mode' must be 'add' or 'replace'",
                    key=key,
                )
            )
        ids = self._lookup_ids(
            Model, val.get("records", []), company_domain, key, auto_create
        )
        ids = list(dict.fromkeys(ids))  # an item given twice is linked once
        if mode == "replace":
            return [Command.set(ids)]
        return [Command.link(rec_id) for rec_id in ids]

    def _lookup_ids(self, Model, items, company_domain, key, auto_create):
        """Return one record ID per lookup item. An item gives field values
        that must all match, e.g. ``{"name": "Customer A"}``, ``{"id": 5}``
        or ``{"name": "VAT 7%", "type_tax_use": "sale"}``.

        Each item must match exactly one record. When some items match
        nothing, the ``auto_create`` values of ``key`` are created once and
        the lookup runs again.
        """
        for item in items:
            if not isinstance(item, dict) or not item:
                raise ValidationError(
                    self.env._(
                        "'%(key)s': a lookup must be a dict of field values, "
                        'e.g. {"name": "X"}, not %(val)s',
                        key=key,
                        val=item,
                    )
                )
        matches = self._match_lookups(Model, items, company_domain)
        if auto_create.get(key) and not all(matches):
            self._do_auto_create(Model, key, auto_create)
            matches = self._match_lookups(Model, items, company_domain)
        for item, records in zip(items, matches, strict=True):
            # As sent: translations format a dict as the list of its keys
            val = json.dumps(item, ensure_ascii=False, default=str)
            if not records:
                raise ValidationError(
                    self.env._("'%(key)s': %(val)s found no match.", key=key, val=val)
                )
            if len(records) > 1:
                raise ValidationError(
                    self.env._(
                        "'%(key)s': %(val)s matched more than 1 record, "
                        "add a field to the lookup or use its id",
                        key=key,
                        val=val,
                    )
                )
        return [records.id for records in matches]

    def _match_lookups(self, Model, items, company_domain):
        """Records matching each lookup item. Items with one stored char,
        integer or selection field (or the id) and one plain value are
        searched together, one query per field, then matched on their value
        as converted for the database. Other items are searched one by one,
        so that the database decides."""

        def scope(fnames):
            # An id is unique: not company scoped, record rules still apply
            return None if "id" in fnames else company_domain

        def batch_value(item):
            """Value of the item as stored, None when it is not batched"""
            if len(item) != 1:
                return None
            fname, value = next(iter(item.items()))
            field = Model._fields.get(fname)
            # Lists, empty strings (SQL matches NULL too), floats, booleans
            if (
                not field
                or not isinstance(value, int | str)
                or isinstance(value, bool)
                or value == ""
            ):
                return None
            if fname == "id":
                return int(value) if str(value).isdigit() else None
            if field.store and not field.search and field.type in BATCH_TYPES:
                return field.convert_to_cache(value, Model, validate=False)
            return None

        values_by_field = defaultdict(set)
        for item in items:
            value = batch_value(item)
            if value is not None:
                values_by_field[next(iter(item))].add(value)
        found = {}  # {(field, stored value): records}
        for fname, values in values_by_field.items():
            records = self._call_field_search_cache(
                Model, [(fname, "in", list(values))], scope([fname])
            )
            for rec in records:
                key = (fname, rec[fname])
                found[key] = found.get(key, Model.browse()) | rec
        matches = []
        for item in items:
            value = batch_value(item)
            if value is None:
                records = self._call_field_search_cache(
                    Model, self._lookup_domain(item), scope(item)
                )
            else:
                records = found.get((next(iter(item)), value), Model.browse())
            matches.append(records)
        return matches

    @api.model
    def _finalize_data_to_write(self, rec, rec_dict, auto_create=False, company=None):
        """Resolve relational field values in rec_dict to ORM-ready IDs/commands.

        - many2one  : ``{"lookup_field": value}`` -> integer ID
        - many2many : ``[{"lookup_field": val}, ...]`` -> [(4/6, ...)] commands
        - other fields are passed through unchanged.

        Lookups of check_company fields are scoped on the company_id of
        rec_dict, else on ``company``, else on env.company.
        """
        auto_create = auto_create or {}
        if company is None:
            company = self.env.company.id
        final_dict = {}
        # company_id first, it scopes the other lookups
        for key in sorted(rec_dict, key=lambda key: key != "company_id"):
            value = rec_dict[key]
            field = rec._fields.get(key)
            # many2one: {"field": "value"} or {"id": 5}
            # many2many: {"mode": "add"|"replace", "records": [...]}
            if (
                field
                and field.type in ("many2one", "many2many")
                and isinstance(value, dict)
                and value
            ):
                value = self._process_many2_field(
                    field, value, final_dict.get("company_id", company), auto_create
                )
            final_dict[key] = value
        return final_dict

    @api.model
    def create_data(self, model, vals):
        _logger.info("[%s].create_data(), input: %s", model, vals)
        res = self._check_result_field(model, vals) or self.friendly_create_data(
            model, vals
        )
        if res["is_success"]:
            record = self.env[model].browse(res["result"]["id"])
            self._add_result_records(res, record, vals)
        _logger.info("[%s].create_data(), output: %s", model, res)
        return res

    @api.model
    def update_data(self, model, vals):
        _logger.info("[%s].update_data(), input: %s", model, vals)
        res = self._check_result_field(model, vals) or self.friendly_update_data(
            model, vals
        )
        if res["is_success"]:
            records = self.env[model].browse(res["result"]["id"])
            # search_key values are echoed, but 'id' stays the updated ids: the
            # callback URL is linked to them as superuser
            res["result"] = {**vals.get("search_key", {}), "id": records.ids}
            self._add_result_records(res, records, vals)
        _logger.info("[%s].update_data(), output: %s", model, res)
        return res

    @api.model
    def create_update_data(self, model, vals):
        _logger.info("[%s].create_update_data(), input: %s", model, vals)
        if not self._search_object(model, vals):
            return self.create_data(model, vals)  # fall back to create
        return self.update_data(model, vals)

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
        _logger.info("[%s].search_data(), input: %s", model, vals)
        result = self._common_search_data(model, vals)
        res = {
            "is_success": True,
            "result": result,
            "messages": self.env._("Record search successfully"),
        }
        _logger.info("[%s].search_data(), output: %s", model, res)
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
                        Only public methods are allowed (no '_' prefix
                        or @api.private), same as RPC.
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

        # Same guard as RPC: block private ('_' prefix / @api.private) methods
        func = get_public_method(rec, method_name)
        result = func(rec, **(parameter or {}))
        return {
            "is_success": True,
            "result": result,
            "messages": self.env._(
                "Function '%(method)s' called successfully", method=method_name
            ),
        }
