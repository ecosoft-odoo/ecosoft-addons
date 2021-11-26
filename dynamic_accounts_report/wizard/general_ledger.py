# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GeneralView(models.TransientModel):
    _name = "account.general.ledger"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Journals",
        required=True,
        default=[],
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Accounts",
    )
    account_tag_ids = fields.Many2many(
        comodel_name="account.account.tag",
        string="Account Tags",
    )
    analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        string="Analytic Accounts",
    )
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
    )
    display_account = fields.Selection(
        selection=[
            ("all", "All"),
            ("movement", "With movements"),
            ("not_zero", "With balance is not equal to 0"),
        ],
        string="Display Accounts",
        required=True,
        default="movement",
    )
    target_move = fields.Selection(
        selection=[
            ("all", "All"),
            ("posted", "Posted"),
        ],
        string="Target Move",
        required=True,
        default="posted",
    )
    date_from = fields.Date(
        string="Start date",
    )
    date_to = fields.Date(
        string="End date",
    )
    operating_unit_ids = fields.Many2many(
        comodel_name="operating.unit",
        string="Operating Unit",
    )

    @api.model
    def create(self, vals):
        context = self._context.copy()
        if context.get("account_id"):
            vals.update({"account_ids": [(6, 0, [context["account_id"]])]})
        if context.get("wizard_id"):
            report = self.env["dynamic.balance.sheet.report"].browse(
                context["wizard_id"]
            )
            vals.update(
                {
                    "company_id": report.company_id.id,
                    "journal_ids": report.journal_ids
                    and [(6, 0, report.journal_ids.ids)]
                    or False,
                    "account_tag_ids": report.account_tag_ids
                    and [(6, 0, report.account_tag_ids.ids)]
                    or False,
                    "analytic_ids": report.analytic_ids
                    and [(6, 0, report.analytic_ids.ids)]
                    or False,
                    "analytic_tag_ids": report.analytic_tag_ids
                    and [(6, 0, report.analytic_tag_ids.ids)]
                    or False,
                    "display_account": report.display_account,
                    "target_move": report.target_move,
                    "date_from": report.date_from,
                    "date_to": report.date_to,
                    "operating_unit_ids": report.operating_unit_ids
                    and [(6, 0, report.operating_unit_ids.ids)]
                    or False,
                }
            )
        return super().create(vals)

    def get_filter_data(self, option):
        r = self.env["account.general.ledger"].search([("id", "=", option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [("company_id", "=", company_id.id)]
        journals = (
            r.journal_ids
            if r.journal_ids
            else self.env["account.journal"].search(company_domain)
        )
        analytics = (
            r.analytic_ids
            if r.analytic_ids
            else self.env["account.analytic.account"].search(company_domain)
        )
        operating_units = (
            r.operating_unit_ids
            if r.operating_unit_ids
            else self.env["operating.unit"].search(company_domain)
        )
        account_tags = (
            r.account_tag_ids
            if r.account_tag_ids
            else self.env["account.account.tag"].search([])
        )
        analytic_tags = (
            r.analytic_tag_ids
            if r.analytic_tag_ids
            else self.env["account.analytic.tag"]
            .sudo()
            .search(
                ["|", ("company_id", "=", company_id.id), ("company_id", "=", False)]
            )
        )
        if r.account_tag_ids:
            company_domain.append(("tag_ids", "in", r.account_tag_ids.ids))
        accounts = (
            r.account_ids
            if r.account_ids
            else self.env["account.account"].search(company_domain)
        )
        filter_dict = {
            "journal_ids": r.journal_ids.ids,
            "account_ids": r.account_ids.ids,
            "analytic_ids": r.analytic_ids.ids,
            "operating_unit_ids": r.operating_unit_ids.ids,
            "company_id": company_id.id,
            "date_from": r.date_from,
            "date_to": r.date_to,
            "target_move": r.target_move,
            "journals_list": [(j.id, j.name, j.code) for j in journals],
            "accounts_list": [(a.id, a.name) for a in accounts],
            "analytic_list": [(anl.id, anl.name) for anl in analytics],
            "operating_unit_list": [
                (ou.id, ou.name, ou.code) for ou in operating_units
            ],
            "company_name": company_id and company_id.name,
            "analytic_tag_ids": r.analytic_tag_ids.ids,
            "analytic_tag_list": [(anltag.id, anltag.name) for anltag in analytic_tags],
            "account_tag_ids": r.account_tag_ids.ids,
            "account_tag_list": [(a.id, a.name) for a in account_tags],
        }
        filter_dict.update(default_filters)
        return filter_dict

    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}
        if data.get("journal_ids"):
            filters["journals"] = (
                self.env["account.journal"]
                .browse(data.get("journal_ids"))
                .mapped("code")
            )
        else:
            filters["journals"] = ["All"]
        if data.get("account_ids", []):
            filters["accounts"] = (
                self.env["account.account"]
                .browse(data.get("account_ids", []))
                .mapped("code")
            )
        else:
            filters["accounts"] = ["All"]
        if data.get("target_move"):
            filters["target_move"] = data.get("target_move")
        else:
            filters["target_move"] = "posted"
        if data.get("date_from"):
            filters["date_from"] = data.get("date_from")
        else:
            filters["date_from"] = False
        if data.get("date_to"):
            filters["date_to"] = data.get("date_to")
        else:
            filters["date_to"] = False
        if data.get("analytic_ids", []):
            filters["analytics"] = (
                self.env["account.analytic.account"]
                .browse(data.get("analytic_ids", []))
                .mapped("name")
            )
        else:
            filters["analytics"] = ["All"]

        if data.get("account_tag_ids"):
            filters["account_tags"] = (
                self.env["account.account.tag"]
                .browse(data.get("account_tag_ids", []))
                .mapped("name")
            )
        else:
            filters["account_tags"] = ["All"]

        if data.get("analytic_tag_ids", []):
            filters["analytic_tags"] = (
                self.env["account.analytic.tag"]
                .browse(data.get("analytic_tag_ids", []))
                .mapped("name")
            )
        else:
            filters["analytic_tags"] = ["All"]

        if data.get("operating_unit_ids"):
            filters["operating_units"] = (
                self.env["operating.unit"]
                .browse(data.get("operating_unit_ids"))
                .mapped("code")
            )
        else:
            filters["operating_units"] = ["All"]

        filters["company_id"] = ""
        filters["accounts_list"] = data.get("accounts_list")
        filters["journals_list"] = data.get("journals_list")
        filters["analytic_list"] = data.get("analytic_list")
        filters["account_tag_list"] = data.get("account_tag_list")
        filters["analytic_tag_list"] = data.get("analytic_tag_list")
        filters["company_name"] = data.get("company_name")
        filters["target_move"] = data.get("target_move").capitalize()
        filters["operating_unit_list"] = data.get("operating_unit_list")
        return filters

    def _get_accounts(self, accounts, init_balance, display_account, data):
        cr = self.env.cr
        MoveLine = self.env["account.move.line"]
        move_lines = {x: [] for x in accounts.ids}

        # Prepare initial sql query and Get the initial move lines
        if init_balance and data.get("date_from"):
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get("date_from"), date_to=False,
                initial_bal=True)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace("account_move_line__move_id",
                                           "m").replace("account_move_line",
                                                        "l")
            new_filter = filters
            if data["target_move"] == "posted":
                new_filter += " AND m.state = 'posted'"
            else:
                new_filter += " AND m.state in ('draft', 'posted')"

            if data.get("date_from"):
                new_filter += " AND l.date < '%s'" % data.get("date_from")

            if data["journals"]:
                new_filter += " AND j.id IN %s" % str(tuple(data["journals"].ids) + tuple([0]))

            if data.get("accounts"):
                WHERE = "WHERE l.account_id IN %s" % str(tuple(data.get("accounts").ids) + tuple([0]))
            else:
                WHERE = "WHERE l.account_id IN %s"

            if data.get("analytics"):
                WHERE += " AND anl.id IN %s" % str(tuple(data.get("analytics").ids) + tuple([0]))

            if data.get("analytic_tags"):
                WHERE += " AND anltag.account_analytic_tag_id IN %s" % str(
                    tuple(data.get("analytic_tags").ids) + tuple([0]))

            if data["operating_units"]:
                WHERE += " AND l.operating_unit_id IN %s" % str(
                    tuple(data.get("operating_units").ids) + tuple([0])
            )

            sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                        '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                        NULL AS currency_id,\
                        '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                        '' AS partner_name\
                        FROM account_move_line l\
                        LEFT JOIN account_move m ON (l.move_id=m.id)\
                        LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                        LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                        LEFT JOIN account_move i ON (m.id =i.id)\
                        LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                        LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                        LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                        JOIN account_journal j ON (l.journal_id=j.id)"""
                        + WHERE + new_filter + " GROUP BY l.account_id")
            if data.get("accounts"):
                params = tuple(init_where_params)
            else:
                params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)

            for row in cr.dictfetchall():
                row["m_id"] = row["account_id"]
                move_lines[row.pop("account_id")].append(row)

        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        final_filters = " AND ".join(wheres)
        final_filters = final_filters.replace(
            "account_move_line__move_id", "m"
        ).replace("account_move_line", "l")
        new_final_filter = final_filters

        if data["target_move"] == "posted":
            new_final_filter += " AND m.state = 'posted'"
        else:
            new_final_filter += " AND m.state in ('draft','posted')"

        if data.get("date_from"):
            new_final_filter += " AND l.date >= '%s'" % data.get("date_from")
        if data.get("date_to"):
            new_final_filter += " AND l.date <= '%s'" % data.get("date_to")

        if data["journals"]:
            new_final_filter += " AND j.id IN %s" % str(
                tuple(data["journals"].ids) + tuple([0])
            )

        if data.get("accounts"):
            WHERE = "WHERE l.account_id IN %s" % str(
                tuple(data.get("accounts").ids) + tuple([0])
            )
        else:
            WHERE = "WHERE l.account_id IN %s"

        if data["analytics"]:
            WHERE += " AND anl.id IN %s" % str(
                tuple(data.get("analytics").ids) + tuple([0])
            )

        if data["analytic_tags"]:
            WHERE += " AND anltag.account_analytic_tag_id IN %s" % str(
                tuple(data.get("analytic_tags").ids) + tuple([0])
            )

        if data["operating_units"]:
            WHERE += " AND l.operating_unit_id IN %s" % str(
                tuple(data.get("operating_units").ids) + tuple([0])
            )

        # Get move lines base on sql query and Calculate the total balance of move lines
        sql = (
            """SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id,
                    l.date AS ldate, j.code AS lcode, l.currency_id,
                    l.amount_currency, l.ref AS lref,
                    l.name AS lname, COALESCE(l.debit,0) AS debit,
                    COALESCE(l.credit,0) AS credit,
                    COALESCE(SUM(l.balance),0) AS balance,\
                    m.name AS move_name, c.symbol AS currency_code,
                    c.position AS currency_position, p.name AS partner_name\
                    FROM account_move_line l\
                    JOIN account_move m ON (l.move_id = m.id)\
                    LEFT JOIN res_currency c ON (l.currency_id = c.id)\
                    LEFT JOIN res_partner p ON (l.partner_id = p.id)\
                    LEFT JOIN account_analytic_account anl
                        ON (l.analytic_account_id = anl.id)\
                    LEFT JOIN account_analytic_tag_account_move_line_rel anltag
                        ON (anltag.account_move_line_id = l.id)\
                    JOIN account_journal j ON (l.journal_id = j.id)\
                    JOIN account_account acc ON (l.account_id = acc.id) """
            + WHERE
            + new_final_filter
            + """ GROUP BY l.id, m.id, l.account_id,
                l.date, j.code, l.currency_id, l.amount_currency, l.ref,
                l.name, m.name, c.symbol, c.position, p.name"""
        )
        if data.get("accounts"):
            params = tuple(where_params)
        else:
            params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row["account_id"]):
                balance += round(line["debit"], 2) - round(line["credit"], 2)
            row["balance"] += round(balance, 2)
            row["m_id"] = row["account_id"]
            move_lines[row.pop("account_id")].append(row)
        # Calculate the debit, credit and balance for Accounts
        account_res = []
        for account in accounts:
            currency = (
                account.currency_id
                and account.currency_id
                or account.company_id.currency_id
            )
            res = {fn: 0.0 for fn in ["credit", "debit", "balance"]}
            res["code"] = account.code
            res["name"] = account.name
            res["id"] = account.id
            res["move_lines"] = move_lines[account.id]
            for line in res.get("move_lines"):
                res["debit"] += round(line["debit"], 2)
                res["credit"] += round(line["credit"], 2)
                res["balance"] = round(line["balance"], 2)
            if display_account == "all":
                account_res.append(res)
            if display_account == "movement" and res.get("move_lines"):
                account_res.append(res)
            if display_account == "not_zero" and not currency.is_zero(res["balance"]):
                account_res.append(res)
        return account_res

    def _get_report_values(self, data):
        docs = data["model"]
        display_account = data["display_account"]
        init_balance = True
        accounts = self.env["account.account"].search([])
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))
        account_res = self._get_accounts(accounts, init_balance, display_account, data)
        debit_total = 0
        debit_total = sum(x["debit"] for x in account_res)
        credit_total = sum(x["credit"] for x in account_res)
        debit_balance = round(debit_total, 2) - round(credit_total, 2)
        return {
            "doc_ids": self.ids,
            "debit_total": debit_total,
            "credit_total": credit_total,
            "debit_balance": debit_balance,
            "docs": docs,
            "time": time,
            "Accounts": account_res,
        }

    @api.model
    def _get_currency(self):
        journal = self.env["account.journal"].browse(
            self.env.context.get("default_journal_id", False)
        )
        if journal.currency_id:
            return journal.currency_id.id
        lang = self.env.user.lang
        if not lang:
            lang = "en_US"
        lang = lang.replace("_", "-")
        currency_array = [
            self.env.company.currency_id.symbol,
            self.env.company.currency_id.position,
            lang,
        ]
        return currency_array

    @api.model
    def view_report(self, option, title):
        r = self.env["account.general.ledger"].search([("id", "=", option[0])])
        data = {
            "display_account": r.display_account,
            "model": self,
            "journals": r.journal_ids,
            "target_move": r.target_move,
            "accounts": r.account_ids,
            "account_tags": r.account_tag_ids,
            "analytics": r.analytic_ids,
            "analytic_tags": r.analytic_tag_ids,
            "operating_units": r.operating_unit_ids,
        }
        if r.date_from:
            data.update(
                {
                    "date_from": r.date_from,
                }
            )
        if r.date_to:
            data.update(
                {
                    "date_to": r.date_to,
                }
            )

        company_id = self.env.company
        company_domain = [("company_id", "=", company_id.id)]
        if r.account_tag_ids:
            company_domain.append(("tag_ids", "in", r.account_tag_ids.ids))
        if r.account_ids:
            company_domain.append(("id", "in", r.account_ids.ids))

        new_account_ids = self.env["account.account"].search(company_domain)
        data.update({"accounts": new_account_ids})
        filters = self.get_filter(option)
        records = self._get_report_values(data)

        if filters["account_tags"] != ["All"]:
            tag_accounts = list(map(lambda x: x.code, new_account_ids))

            def filter_code(rec_dict):
                if rec_dict["code"] in tag_accounts:
                    return True
                else:
                    return False

            new_records = list(filter(filter_code, records["Accounts"]))
            records["Accounts"] = new_records
        currency = self._get_currency()
        return {
            "name": title,
            "type": "ir.actions.client",
            "tag": "g_l",
            "filters": filters,
            "report_lines": records["Accounts"],
            "debit_total": records["debit_total"],
            "credit_total": records["credit_total"],
            "debit_balance": records["debit_balance"],
            "currency": currency,
        }
