# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)


from odoo import fields, models


class StockInventoryReportWizard(models.TransientModel):
    _name = "stock.inventory.report.wizard"
    _description = "Wizard for Stock Inventory Report"

    # Search Criteria
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        string="Company",
        required=True,
        ondelete="cascade",
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
    )
    location_ids = fields.Many2many(
        comodel_name="stock.location",
        domain="[('usage','=','internal'), "
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    show_zero_stock = fields.Boolean(
        default=True,
    )
    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name="stock.inventory.report.view",
        compute="_compute_results",
        help="Use compute fields, so there is nothing store in database",
    )

    def button_export_html(self):
        self.ensure_one()
        report_type = "qweb-html"
        return self._print_report(report_type)

    def button_export_pdf(self):
        self.ensure_one()
        report_type = "qweb-pdf"
        return self._print_report(report_type)

    def button_export_xlsx(self):
        self.ensure_one()
        report_type = "xlsx"
        return self._print_report(report_type)

    def _print_report(self, report_type):
        self.ensure_one()
        if report_type == "xlsx":
            report_name = "stock_report_xlsx.report_stock_inventory_xlsx"
        else:
            report_name = "stock_report_xlsx.report_stock_inventory"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, config=False)
        )

    def _get_report_base_filename(self):
        self.ensure_one()
        return "StockInventory-{}".format(self._get_date_today())

    def _get_header_name(self):
        """Hooks header name here"""
        return "Stock Inventory Report"

    def _get_date_today(self):
        return fields.Date.context_today(self)

    def _query_select(self):
        return "product_id, location_id, sum(quantity) as quantity"

    def _query_groupby(self):
        return "product_id, location_id"

    def _query_having(self):
        if not self.show_zero_stock:
            return "HAVING sum(quantity) != 0.0"
        return ""

    def _query_orderby(self):
        return "location_id, product_id"

    def _domain_where_clause(self):
        # Get all product
        if not (self.location_ids or self.product_ids):
            return ""

        condition = []
        if self.location_ids:
            op = "in"
            if len(self.location_ids) == 1:
                op = "="
            condition.append(
                "location_id %(op)s %(location)s"
                % {
                    "op": op,
                    "location": tuple(self.location_ids.ids)
                    if op == "in"
                    else self.location_ids.id,
                }
            )
        if self.product_ids:
            op = "in"
            if len(self.product_ids) == 1:
                op = "="
            condition.append(
                "product_id %(op)s %(location)s"
                % {
                    "op": op,
                    "location": tuple(self.product_ids.ids)
                    if op == "in"
                    else self.product_ids.id,
                }
            )
        condition = " AND ".join(condition)
        # add AND first condition
        if condition:
            condition = "AND " + condition
        return condition

    def _compute_results(self):
        self.ensure_one()
        domain = self._domain_where_clause()
        self._cr.execute(
            """
                SELECT {} FROM stock_quant
                WHERE company_id = %s {}
                GROUP BY {}
                {}  -- optional
                ORDER BY {}
            """.format(
                self._query_select(),
                domain,
                self._query_groupby(),
                self._query_having(),
                self._query_orderby(),
            ),
            (self.company_id.id,),
        )
        tax_report_results = self._cr.dictfetchall()
        StockInventoryObj = self.env["stock.inventory.report.view"]
        self.results = False
        for line in tax_report_results:
            self.results += StockInventoryObj.new(line)


class StockInventoryReportView(models.TransientModel):
    _name = "stock.inventory.report.view"
    _description = "Stock Inventory Report View"
    _order = "id"

    company_id = fields.Many2one(comodel_name="res.company")
    product_id = fields.Many2one(comodel_name="product.product")
    location_id = fields.Many2one(comodel_name="stock.location")
    quantity = fields.Float()
