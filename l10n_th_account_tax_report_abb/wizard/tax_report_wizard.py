# Copyright 2024 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class TaxReportWizard(models.TransientModel):
    _inherit = "tax.report.wizard"

    def _compute_results(self):
        self.ensure_one()
        domain = self._domain_where_clause_tax()
        self._cr.execute(
            """
            SELECT {}
            FROM (
                SELECT {}
                FROM account_move_tax_invoice t
                JOIN account_move_line ml ON ml.id = t.move_line_id
                JOIN account_move m ON m.id = ml.move_id
                WHERE {}
                AND t.tax_invoice_number IS NOT NULL
                AND ml.account_id IN (SELECT DISTINCT account_id
                                        FROM account_tax_repartition_line
                                        WHERE account_id IS NOT NULL
                                        AND invoice_tax_id = %s OR refund_tax_id = %s)
                -- query condition with normal report date by report date
                -- and late report date within range date end
                AND (
                    (t.report_date >= %s AND t.report_date <= %s)
                    OR (
                        t.report_late_mo != '0' AND
                        EXTRACT(MONTH FROM t.report_date) <= %s AND
                        EXTRACT(YEAR FROM t.report_date) <= %s AND
                        EXTRACT(MONTH FROM t.report_date) >= %s AND
                        EXTRACT(YEAR FROM t.report_date) >= %s
                    )
                )
                AND ml.company_id = %s
                AND t.reversed_id IS NULL
                AND NOT t.is_tax_abb

                UNION

                -- query tax abb state posted only
                SELECT NULL AS id, t.company_id, NULL AS account_id, NULL AS partner_id,
                    CONCAT(
                        MIN(t.tax_invoice_number),
                        ' - ',
                        MAX(t.tax_invoice_number)
                    ) as tax_invoice_number,
                    NULL AS tax_date,
                    SUM(t.tax_base_amount) AS tax_base_amount, SUM(t.balance) AS tax_amount,
                    'Tax ABB' AS name
                FROM account_move_tax_invoice t
                JOIN account_move_line ml ON ml.id = t.move_line_id
                JOIN account_move m ON m.id = ml.move_id
                WHERE ml.parent_state = 'posted'
                AND t.tax_invoice_number IS NOT NULL
                AND ml.account_id IN (SELECT DISTINCT account_id
                                        FROM account_tax_repartition_line
                                        WHERE account_id is not null
                                        AND invoice_tax_id = %s or refund_tax_id = %s)
                -- query condition with normal report date by report date
                -- and late report date within range date end
                AND (
                    (t.report_date >= %s AND t.report_date <= %s)
                    OR (
                        t.report_late_mo != '0' AND
                        EXTRACT(MONTH FROM t.report_date) <= %s AND
                        EXTRACT(YEAR FROM t.report_date) <= %s AND
                        EXTRACT(MONTH FROM t.report_date) >= %s AND
                        EXTRACT(YEAR FROM t.report_date) >= %s
                    )
                 )
                 AND ml.company_id = %s
                 AND t.reversed_id is null
                 AND t.is_tax_abb
              GROUP BY t.company_id
            ) a
            group by {}
            order by tax_date, tax_invoice_number
        """.format(
                self._query_select_tax(),
                self._query_select_sub_tax(),
                domain,
                self._query_groupby_tax(),
            ),
            (
                self.tax_id.id,
                self.tax_id.id,
                self.date_from,
                self.date_to,
                self.date_to.month,
                self.date_to.year,
                self.date_from.month,
                self.date_from.year,
                self.company_id.id,
                # tax abb
                self.tax_id.id,
                self.tax_id.id,
                self.date_from,
                self.date_to,
                self.date_to.month,
                self.date_to.year,
                self.date_from.month,
                self.date_from.year,
                self.company_id.id,
            ),
        )
        tax_report_results = self._cr.dictfetchall()
        ReportLine = self.env["tax.report.view"]
        self.results = False
        for line in tax_report_results:
            self.results += ReportLine.new(line)
