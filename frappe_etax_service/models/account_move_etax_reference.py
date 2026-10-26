# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

LOCKED_ETAX_STATUSES = ("success", "processing", "replace")


class AccountMoveEtaxReference(models.Model):
    _name = "account.move.etax.reference"
    _description = "e-Tax Reference Document"
    _order = "move_id, sequence, id"

    move_id = fields.Many2one(
        comodel_name="account.move",
        required=True,
        index=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="move_id.company_id")
    currency_id = fields.Many2one(related="move_id.currency_id")
    commercial_partner_id = fields.Many2one(related="move_id.commercial_partner_id")
    ref_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Odoo Invoice",
        index="btree_not_null",
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),"
        " ('company_id', '=', company_id),"
        " ('commercial_partner_id', '=', commercial_partner_id)]",
        help="Leave empty for tax invoices that are not in Odoo.",
    )
    name = fields.Char(
        string="Reference No.",
        size=35,
        compute="_compute_from_ref_move",
        store=True,
        readonly=False,
    )
    date = fields.Date(
        string="Reference Date",
        compute="_compute_from_ref_move",
        store=True,
        readonly=False,
    )
    type_code_id = fields.Many2one(
        comodel_name="etax.doctype.code",
        string="Document Type",
        compute="_compute_from_ref_move",
        store=True,
        readonly=False,
    )
    amount_untaxed = fields.Monetary(
        string="Original Untaxed Amount",
        compute="_compute_from_ref_move",
        store=True,
        readonly=False,
        help="Untaxed amount of the referenced tax invoice.",
    )
    credit_amount = fields.Monetary(
        string="Adjusted Amount",
        help="Untaxed amount of this note allocated to the referenced invoice.",
    )

    @api.depends("ref_move_id")
    def _compute_from_ref_move(self):
        t02 = self.env.ref(
            "frappe_etax_service.etax_doctype_code_T02", raise_if_not_found=False
        )
        for rec in self:
            ref_move = rec.ref_move_id
            if ref_move:
                rec.name = ref_move.name
                rec.date = ref_move.invoice_date
                rec.amount_untaxed = ref_move.amount_untaxed
            rec.type_code_id = (
                ref_move.etax_doctype_id.doctype_code_id or rec.type_code_id or t02
            )

    @api.constrains("move_id", "name", "ref_move_id")
    def _check_unique_reference(self):
        for move in self.move_id:
            origin = move.debit_origin_id or move.reversed_entry_id
            names = [origin.name] if origin else []
            for ref in move.etax_reference_ids:
                if origin and ref.ref_move_id == origin:
                    raise ValidationError(
                        self.env._(
                            "%(ref)s is already the origin of %(move)s.",
                            ref=origin.name,
                            move=move.display_name,
                        )
                    )
                if ref.name in names:
                    raise ValidationError(
                        self.env._(
                            "Reference %(ref)s is used more than once on %(move)s.",
                            ref=ref.name,
                            move=move.display_name,
                        )
                    )
                names.append(ref.name)

    def _check_etax_editable(self):
        locked = self.move_id.filtered(lambda m: m.etax_status in LOCKED_ETAX_STATUSES)
        if locked:
            raise ValidationError(
                self.env._("%s: e-Tax references cannot be changed after signing.")
                % ", ".join(locked.mapped("display_name"))
            )

    @api.model_create_multi
    def create(self, vals_list):
        t02 = self.env.ref(
            "frappe_etax_service.etax_doctype_code_T02", raise_if_not_found=False
        )
        for vals in vals_list:
            if t02 and not vals.get("ref_move_id") and not vals.get("type_code_id"):
                vals["type_code_id"] = t02.id
        records = super().create(vals_list)
        records._check_etax_editable()
        return records

    def write(self, vals):
        self._check_etax_editable()
        return super().write(vals)

    def unlink(self):
        self._check_etax_editable()
        return super().unlink()

    def _prepare_etax_reference(self):
        self.ensure_one()
        return {
            "name": self.name,
            "date": self.date,
            "type_code": self.type_code_id.code,
            "document_name": self.type_code_id.name,
            "amount_untaxed": self.amount_untaxed,
        }
