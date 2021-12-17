# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class DataMapType(models.Model):
    _name = "data.map.type"
    _description = "Type of data map, will be created for each model"

    name = fields.Char(
        string="Name",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="data.map",
        inverse_name="map_type_id",
        string="Map Details",
        ondelete="cascade",
        index=True,
    )
    model = fields.Selection(
        selection=[],
        string="Apply On Model",
        required=True,
        readonly=False,
        index=True,
    )
    template_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Template",
        help="Template used during import/export xlxs",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("name_company_uniq", "unique(name, company_id)", "Name must be unique!"),
    ]


class DataMap(models.Model):
    _name = "data.map"
    _description = "Field mapping database"

    map_type_id = fields.Many2one(
        comodel_name="data.map.type",
        string="Map Type",
        index=True,
        ondelete="cascade",
        requried=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        index=True,
    )
    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Field",
        domain="[('model_id', '=', model_id)]",
        ondelete="cascade",
        index=True,
        required=True,
    )
    in_value = fields.Char(
        string="Input Value",
        index=True,
        help="Odoo's value, searchable by name_search",
    )
    out_value = fields.Char(
        string="Output Value",
        index=True,
        help="Mapped output value",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="map_type_id.company_id",
        store=True,
    )

    _sql_constraints = [
        (
            "in_value_uniq",
            "unique(map_type_id, model_id, field_id, in_value)",
            "In value must be unique!",
        ),
    ]

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.field_id = False

    def write(self, vals):
        if "field_id" in vals:
            if not vals["field_id"]:
                vals["model_id"] = False
            elif not vals.get("model_id", False):
                field = self.env["ir.model.fields"].browse(vals["field_id"])
                vals["model_id"] = field.model_id.id
        return super().write(vals)

    @api.model
    def get_out_value(self, map_type, model, field, in_value=False):
        """
        map_type = Name of mapping type
        model = Name of model, i.e., account.account
        field = Database field, i.e., code
        in_value = Value in Ecosoft
        return: out_value
        """
        out_value = False
        if in_value:
            in_value = str(in_value)
            if in_value[-2:] == ".0":
                in_value = in_value[:-2]
            out_value = self.search(
                [
                    ("map_type_id.name", "=", map_type),
                    ("model_id.model", "=", model),
                    ("field_id.name", "=", field),
                    ("in_value", "=", in_value),
                ],
                limit=1,
            ).out_value
        if isinstance(out_value, str):
            out_value = out_value.encode("utf-8")
        return out_value

    @api.model
    def get_in_value(self, map_type, model, field, out_value=False):
        """
        map_type = Name of mapping type
        model = Name of model, i.e., account.account
        field = Database field, i.e., code
        out_value = Value of other system
        return: in_value
        """
        in_value = False
        if out_value:
            out_value = str(out_value)
            if out_value[-2:] == ".0":
                out_value = out_value[:-2]
            in_value = self.search(
                [
                    ("map_type_id.name", "=", map_type),
                    ("model_id.model", "=", model),
                    ("field_id.name", "=", field),
                    ("out_value", "=", out_value),
                ],
                limit=1,
            ).in_value
        return in_value
