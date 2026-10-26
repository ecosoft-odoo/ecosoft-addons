# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class EtaxMultiCreditNoteWizard(models.TransientModel):
    _name = "etax.multi.credit.note.wizard"
    _description = "Create one credit note referencing many invoices"

    company_id = fields.Many2one(comodel_name="res.company", readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", readonly=True)
    partner_id = fields.Many2one(comodel_name="res.partner", readonly=True)
    invoice_ids = fields.Many2many(comodel_name="account.move", readonly=True)
    available_product_ids = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_available_product_ids",
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Products to Credit",
        domain="[('id', 'in', available_product_ids)]",
        help="Only invoice lines of these products are credited. "
        "Leave empty to credit every product.",
    )
    date = fields.Date(
        string="Credit Note Date",
        required=True,
        default=fields.Date.context_today,
    )
    name = fields.Char(
        string="Description",
        help="Label of the credit note lines. Defaults to the invoice line label.",
    )
    purpose_code_id = fields.Many2one(
        comodel_name="etax.purpose.code",
        string="eTax Refund Reason",
        domain="[('etax_doctype_code_ids.code', '=', '81')]",
    )
    reason = fields.Char(
        compute="_compute_reason",
        store=True,
        readonly=False,
    )
    credit_method = fields.Selection(
        selection=[("percent", "Percent"), ("amount", "Total Amount")],
        string="Credit By",
        required=True,
        default="percent",
    )
    credit_percent = fields.Float(string="Percent (%)", digits=(16, 2))
    total_amount = fields.Monetary(string="Total Credit (Untaxed)")
    line_ids = fields.One2many(
        comodel_name="etax.multi.credit.note.wizard.line",
        inverse_name="wizard_id",
        compute="_compute_line_ids",
        store=True,
        readonly=False,
    )
    allocated_amount = fields.Monetary(compute="_compute_allocated_amount")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") != "account.move":
            return res
        invoices = self.env["account.move"].browse(
            self.env.context.get("active_ids", [])
        )
        self._check_invoices(invoices)
        res.update(
            {
                "company_id": invoices.company_id.id,
                "currency_id": invoices.currency_id.id,
                "partner_id": invoices.partner_id.id,
                "invoice_ids": [Command.set(invoices.ids)],
            }
        )
        return res

    @api.model
    def _check_invoices(self, invoices):
        if not invoices:
            raise UserError(self.env._("Select at least one customer invoice."))
        invalid = invoices.filtered(
            lambda m: m.move_type != "out_invoice" or m.state != "posted"
        )
        if invalid:
            raise UserError(
                self.env._("Only posted customer invoices can be selected: %s")
                % ", ".join(invalid.mapped("display_name"))
            )
        for field, label in (
            ("company_id", self.env._("company")),
            ("partner_id", self.env._("customer and branch")),
            ("currency_id", self.env._("currency")),
        ):
            if len(invoices[field]) > 1:
                raise UserError(
                    self.env._("All selected invoices must have the same %s.") % label
                )

    def _get_invoice_lines(self):
        self.ensure_one()
        return self.invoice_ids.sorted(
            lambda m: (m.invoice_date, m.name)
        ).invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.currency_id.compare_amounts(line.price_subtotal, 0) > 0
        )

    @api.depends("invoice_ids")
    def _compute_available_product_ids(self):
        for rec in self:
            rec.available_product_ids = rec._get_invoice_lines().product_id

    @api.depends("invoice_ids", "product_ids")
    def _compute_line_ids(self):
        for rec in self:
            inv_lines = rec._get_invoice_lines()
            products = rec.product_ids._origin
            if products:
                inv_lines = inv_lines.filtered(
                    lambda line, products=products: line.product_id in products
                )
            rec.line_ids = [Command.clear()] + [
                Command.create({"invoice_line_id": line.id}) for line in inv_lines
            ]

    @api.depends("purpose_code_id")
    def _compute_reason(self):
        for rec in self:
            rec.reason = rec.purpose_code_id.reason

    @api.depends("line_ids.credit_amount")
    def _compute_allocated_amount(self):
        for rec in self:
            rec.allocated_amount = sum(rec.line_ids.mapped("credit_amount"))

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def action_calculate(self):
        self.ensure_one()
        lines = self.line_ids
        if not lines:
            raise UserError(self.env._("There is no invoice line to credit."))
        currency = self.currency_id
        if self.credit_method == "percent":
            for line in lines:
                line.credit_amount = currency.round(
                    line.amount_untaxed * self.credit_percent / 100
                )
            return self._reopen()
        base = sum(lines.mapped("amount_untaxed"))
        remaining = self.total_amount
        for line in lines[:-1]:
            amount = currency.round(self.total_amount * line.amount_untaxed / base)
            line.credit_amount = amount
            remaining -= amount
        lines[-1].credit_amount = remaining
        return self._reopen()

    def _check_allocation(self):
        self.ensure_one()
        currency = self.currency_id
        for line in self.line_ids:
            if currency.compare_amounts(line.credit_amount, 0) < 0:
                raise UserError(
                    self.env._("%s: Credit amount cannot be negative.")
                    % line.invoice_line_id.display_name
                )
            if currency.compare_amounts(line.credit_amount, line.remaining_amount) > 0:
                raise UserError(
                    self.env._(
                        "%(line)s: Credit amount %(amount)s exceeds "
                        "the remaining amount %(remaining)s.",
                        line=line.invoice_line_id.display_name,
                        amount=line.credit_amount,
                        remaining=line.remaining_amount,
                    )
                )
        for invoice in self.line_ids.invoice_id:
            credit = sum(
                self.line_ids.filtered(
                    lambda line, inv=invoice: line.invoice_id == inv
                ).mapped("credit_amount")
            )
            remaining = invoice.amount_untaxed - invoice.etax_credited_amount
            if currency.compare_amounts(credit, remaining) > 0:
                raise UserError(
                    self.env._(
                        "%(invoice)s: Credit amount %(amount)s exceeds "
                        "the remaining amount %(remaining)s.",
                        invoice=invoice.name,
                        amount=credit,
                        remaining=remaining,
                    )
                )
        if currency.compare_amounts(self.allocated_amount, 0) <= 0:
            raise UserError(self.env._("Enter a credit amount on at least one line."))
        if (
            self.credit_method == "amount"
            and currency.compare_amounts(self.allocated_amount, self.total_amount) > 0
        ):
            raise UserError(
                self.env._(
                    "The allocated amount %(allocated)s exceeds "
                    "the total credit %(total)s.",
                    allocated=self.allocated_amount,
                    total=self.total_amount,
                )
            )

    def _prepare_credit_note_line_vals(self, line):
        self.ensure_one()
        inv_line = line.invoice_line_id
        taxes = inv_line.tax_ids
        price_include = taxes.filtered("price_include")
        price_unit = (
            price_include.compute_all(
                line.credit_amount, self.currency_id, handle_price_include=False
            )["total_included"]
            if price_include
            else line.credit_amount
        )
        return {
            "product_id": inv_line.product_id.id,
            "name": self.name or inv_line.name,
            "account_id": inv_line.account_id.id,
            "quantity": 1,
            "product_uom_id": inv_line.product_uom_id.id,
            "price_unit": price_unit,
            "tax_ids": [Command.set(taxes.ids)],
            "analytic_distribution": inv_line.analytic_distribution,
            "etax_origin_line_id": inv_line.id,
        }

    def _prepare_credit_note_vals(self, lines):
        self.ensure_one()
        first = lines[0].invoice_id
        invoices = lines.invoice_id.sorted(lambda m: (m.invoice_date, m.name))
        return {
            "move_type": "out_refund",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "journal_id": first.journal_id.id,
            "fiscal_position_id": first.fiscal_position_id.id,
            "invoice_date": self.date,
            "create_purpose_code": self.purpose_code_id.code,
            "create_purpose": self.reason,
            "etax_reference_ids": [
                Command.create(
                    {
                        "sequence": sequence,
                        "ref_move_id": invoice.id,
                        "credit_amount": sum(
                            lines.filtered(
                                lambda line, inv=invoice: line.invoice_id == inv
                            ).mapped("credit_amount")
                        ),
                    }
                )
                for sequence, invoice in enumerate(invoices, start=1)
            ],
            "invoice_line_ids": [
                Command.create(self._prepare_credit_note_line_vals(line))
                for line in lines
            ],
        }

    def action_create(self):
        self.ensure_one()
        self._check_invoices(self.invoice_ids)
        self._check_allocation()
        lines = self.line_ids.filtered(
            lambda line: self.currency_id.compare_amounts(line.credit_amount, 0) > 0
        )
        credit_note = self.env["account.move"].create(
            self._prepare_credit_note_vals(lines)
        )
        if self.currency_id.compare_amounts(
            credit_note.amount_untaxed, self.allocated_amount
        ):
            raise UserError(
                self.env._(
                    "The credit note untaxed amount %(amount)s differs from "
                    "the allocated amount %(total)s.",
                    amount=credit_note.amount_untaxed,
                    total=self.allocated_amount,
                )
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": credit_note.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "context": {"default_move_type": "out_refund"},
        }


class EtaxMultiCreditNoteWizardLine(models.TransientModel):
    _name = "etax.multi.credit.note.wizard.line"
    _description = "Invoice line credited by a multi-reference credit note"

    wizard_id = fields.Many2one(
        comodel_name="etax.multi.credit.note.wizard",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    invoice_line_id = fields.Many2one(
        comodel_name="account.move.line",
        required=True,
    )
    invoice_id = fields.Many2one(
        related="invoice_line_id.move_id",
        string="Invoice",
    )
    invoice_date = fields.Date(related="invoice_line_id.move_id.invoice_date")
    product_id = fields.Many2one(related="invoice_line_id.product_id")
    name = fields.Char(related="invoice_line_id.name", string="Description")
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        related="invoice_line_id.price_subtotal",
    )
    credited_amount = fields.Monetary(
        string="Already Credited",
        related="invoice_line_id.etax_credited_amount",
    )
    remaining_amount = fields.Monetary(
        string="Remaining",
        compute="_compute_remaining_amount",
    )
    credit_amount = fields.Monetary()

    @api.depends("amount_untaxed", "credited_amount")
    def _compute_remaining_amount(self):
        for line in self:
            line.remaining_amount = line.amount_untaxed - line.credited_amount
