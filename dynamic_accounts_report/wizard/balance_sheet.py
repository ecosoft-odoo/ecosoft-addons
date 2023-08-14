# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import io
import json
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class BalanceSheetView(models.TransientModel):
    _name = "dynamic.balance.sheet.report"
    _description = "Dynamic Balance Sheet Report"

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
    debit_credit = fields.Selection(
        selection=[
            ("show", "Show"),
            ("hide", "Hide"),
        ],
        string="Debit/Credit",
        required=True,
        default="show",
    )
    operating_unit_ids = fields.Many2many(
        comodel_name="operating.unit",
        string="Operating Unit",
    )

    @api.model
    def create(self, vals):
        vals.update(
            {
                "target_move": "posted",
                "debit_credit": "hide",
            }
        )
        return super().create(vals)

    def write(self, vals):
        # Target Move
        if vals.get("target_move"):
            vals.update({"target_move": vals.get("target_move").lower()})
        # Journals
        if vals.get("journal_ids"):
            vals.update({"journal_ids": [(6, 0, vals.get("journal_ids"))]})
        if not vals.get("journal_ids"):
            vals.update({"journal_ids": [(5,)]})
        # Accounts
        if vals.get("account_ids"):
            vals.update({"account_ids": [(6, 0, vals.get("account_ids"))]})
        if not vals.get("account_ids"):
            vals.update({"account_ids": [(5,)]})
        # Analytic Account
        if vals.get("analytic_ids"):
            vals.update({"analytic_ids": [(6, 0, vals.get("analytic_ids"))]})
        if not vals.get("analytic_ids"):
            vals.update({"analytic_ids": [(5,)]})
        # Account Tag
        if vals.get("account_tag_ids"):
            vals.update({"account_tag_ids": [(6, 0, vals.get("account_tag_ids"))]})
        if not vals.get("account_tag_ids"):
            vals.update({"account_tag_ids": [(5,)]})
        # Analytic Tag
        if vals.get("analytic_tag_ids"):
            vals.update({"analytic_tag_ids": [(6, 0, vals.get("analytic_tag_ids"))]})
        if not vals.get("analytic_tag_ids"):
            vals.update({"analytic_tag_ids": [(5,)]})
        # Operating Unit
        if vals.get("operating_unit_ids"):
            vals.update(
                {"operating_unit_ids": [(6, 0, vals.get("operating_unit_ids"))]}
            )
        if not vals.get("operating_unit_ids"):
            vals.update({"operating_unit_ids": [(5,)]})
        # Debit/Credit
        if vals.get("debit_credit"):
            vals.update({"debit_credit": vals.get("debit_credit").lower()})
        return super().write(vals)

    def get_filter_data(self, option):
        r = self.env["dynamic.balance.sheet.report"].search([("id", "=", option[0])])
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
            "debit_credit": r.debit_credit,
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
        filters["debit_credit"] = data.get("debit_credit")
        filters["operating_unit_list"] = data.get("operating_unit_list")
        return filters

    # flake8: noqa: C901
    def _get_accounts(self, accounts, init_balance, display_account, data):
        cr = self.env.cr
        MoveLine = self.env["account.move.line"]
        move_lines = {x: [] for x in accounts.ids}

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
        cr.execute(sql, params)  # pylint: disable=sql-injection

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
    def view_report(self, option, tag):
        r = self.env["dynamic.balance.sheet.report"].search([("id", "=", option[0])])
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

        account_report_id = self.env["account.financial.report"].search(
            [("name", "ilike", tag)]
        )

        new_data = {
            "id": self.id,
            "date_from": False,
            "enable_filter": True,
            "debit_credit": True,
            "date_to": False,
            "account_report_id": account_report_id,
            "target_move": filters["target_move"],
            "view_format": "vertical",
            "company_id": self.company_id,
            "used_context": {
                "journal_ids": False,
                "state": filters["target_move"].lower(),
                "date_from": filters["date_from"],
                "date_to": filters["date_to"],
                "strict_range": False,
                "company_id": self.company_id,
                "lang": "en_US",
                "active_test": False,
            },
        }

        account_lines = self.get_account_lines(new_data)
        report_lines = self.view_report_pdf(account_lines, new_data)["report_lines"]
        move_line_accounts = []
        move_lines_dict = {}

        for rec in records["Accounts"]:
            move_line_accounts.append(rec["code"])
            move_lines_dict[rec["code"]] = {}
            move_lines_dict[rec["code"]]["debit"] = rec["debit"]
            move_lines_dict[rec["code"]]["credit"] = rec["credit"]
            move_lines_dict[rec["code"]]["balance"] = rec["balance"]

        report_lines_move = []
        parent_list = []

        def filter_movelines_parents(obj):
            for each in obj:
                if each["report_type"] == "accounts" and each["type"] != "report":
                    if each["code"] in move_line_accounts:
                        report_lines_move.append(each)
                        parent_list.append(each["p_id"])
                elif each["report_type"] == "account_report":
                    report_lines_move.append(each)
                else:
                    report_lines_move.append(each)

        filter_movelines_parents(report_lines)

        for rec in report_lines_move:
            if rec["report_type"] == "accounts" and rec["type"] != "report":
                if rec["code"] in move_line_accounts:
                    rec["debit"] = move_lines_dict[rec["code"]]["debit"]
                    rec["credit"] = move_lines_dict[rec["code"]]["credit"]
                    rec["balance"] = move_lines_dict[rec["code"]]["balance"]

        parent_list = list(set(parent_list))
        max_level = 0
        for rep in report_lines_move:
            if rep["level"] > max_level:
                max_level = rep["level"]

        def get_parents(obj):
            for item in report_lines_move:
                for each in obj:
                    if item["report_type"] != "account_type" and each in item["c_ids"]:
                        obj.append(item["r_id"])
                if item["report_type"] == "account_report":
                    obj.append(item["r_id"])
                    break

        get_parents(parent_list)
        for _i in range(max_level):
            get_parents(parent_list)

        parent_list = list(set(parent_list))
        final_report_lines = []

        for rec in report_lines_move:
            if rec["report_type"] != "accounts" or not rec.get("code"):
                if rec["r_id"] in parent_list:
                    final_report_lines.append(rec)
            else:
                final_report_lines.append(rec)

        def filter_sum(obj):
            sum_list = {}
            for pl in parent_list:
                sum_list[pl] = {}
                sum_list[pl]["s_debit"] = 0
                sum_list[pl]["s_credit"] = 0
                sum_list[pl]["s_balance"] = 0

            for each in obj:
                if each["p_id"] and each["p_id"] in parent_list:
                    sum_list[each["p_id"]]["s_debit"] += each["debit"]
                    sum_list[each["p_id"]]["s_credit"] += each["credit"]
                    sum_list[each["p_id"]]["s_balance"] += each["balance"]
            return sum_list

        def assign_sum(obj):
            for each in obj:
                if (
                    each["r_id"] in parent_list
                    and each["report_type"] != "account_report"
                ):
                    each["debit"] = sum_list_new[each["r_id"]]["s_debit"]
                    each["credit"] = sum_list_new[each["r_id"]]["s_credit"]

        for _p in range(max_level):
            sum_list_new = filter_sum(final_report_lines)
            assign_sum(final_report_lines)

        company_id = self.env.company
        currency = company_id.currency_id
        symbol = currency.symbol
        position = currency.position

        for rec in final_report_lines:
            rec["debit"] = round(rec["debit"], 2)
            rec["credit"] = round(rec["credit"], 2)
            rec["balance"] = rec["debit"] - rec["credit"]
            rec["balance"] = round(rec["balance"], 2)
            if (rec["balance_cmp"] < 0 and rec["balance"] > 0) or (
                rec["balance_cmp"] > 0 and rec["balance"] < 0
            ):
                rec["balance"] = rec["balance"] * -1

            if position == "before":
                rec["m_debit"] = symbol + " " + "{:,.2f}".format(rec["debit"])
                rec["m_credit"] = symbol + " " + "{:,.2f}".format(rec["credit"])
                rec["m_balance"] = symbol + " " + "{:,.2f}".format(rec["balance"])
            else:
                rec["m_debit"] = "{:,.2f}".format(rec["debit"]) + " " + symbol
                rec["m_credit"] = "{:,.2f}".format(rec["credit"]) + " " + symbol
                rec["m_balance"] = "{:,.2f}".format(rec["balance"]) + " " + symbol

        return {
            "name": tag,
            "type": "ir.actions.client",
            "tag": tag,
            "filters": filters,
            "report_lines": records["Accounts"],
            "debit_total": records["debit_total"],
            "credit_total": records["credit_total"],
            "debit_balance": records["debit_balance"],
            "currency": currency,
            "bs_lines": final_report_lines,
        }

    def get_dynamic_xlsx_report(self, options, response, report_data, dfr_data):
        i_data = str(report_data)
        filters = json.loads(options)
        j_data = dfr_data
        rl_data = json.loads(j_data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {"align": "center", "bold": True, "font_size": "20px"}
        )
        sub_heading = workbook.add_format(
            {
                "align": "center",
                "bold": True,
                "font_size": "10px",
                "border": 1,
                "border_color": "black",
            }
        )
        side_heading_main = workbook.add_format(
            {
                "align": "left",
                "bold": True,
                "font_size": "10px",
                "border": 1,
                "border_color": "black",
            }
        )

        side_heading_sub = workbook.add_format(
            {
                "align": "left",
                "bold": True,
                "font_size": "10px",
                "border": 1,
                "border_color": "black",
            }
        )

        side_heading_sub.set_indent(1)
        txt = workbook.add_format({"font_size": "10px", "border": 1})
        txt_name = workbook.add_format({"font_size": "10px", "border": 1})
        txt_name_bold = workbook.add_format(
            {"font_size": "10px", "border": 1, "bold": True}
        )
        txt_name.set_indent(2)
        txt_name_bold.set_indent(2)

        txt = workbook.add_format({"font_size": "10px", "border": 1})

        sheet.merge_range("A2:D3", filters.get("company_name") + " : " + i_data, head)
        date_head = workbook.add_format(
            {"align": "center", "bold": True, "font_size": "10px"}
        )

        date_head.set_align("vcenter")
        date_head.set_text_wrap()
        date_head.set_shrink()
        date_head_left = workbook.add_format(
            {"align": "left", "bold": True, "font_size": "10px"}
        )

        date_head_right = workbook.add_format(
            {"align": "right", "bold": True, "font_size": "10px"}
        )

        date_head_left.set_indent(1)
        date_head_right.set_indent(1)

        if filters.get("date_from"):
            sheet.merge_range(
                "A4:B4", "From: " + filters.get("date_from"), date_head_left
            )
        if filters.get("date_to"):
            sheet.merge_range("C4:D4", "To: " + filters.get("date_to"), date_head_right)

        sheet.merge_range(
            "A5:D6",
            "  Accounts: "
            + ", ".join([lt or "" for lt in filters["accounts"]])
            + ";  Journals: "
            + ", ".join([lt or "" for lt in filters["journals"]])
            + ";  Account Tags: "
            + ", ".join([lt or "" for lt in filters["account_tags"]])
            + ";  Analytic Tags: "
            + ", ".join([lt or "" for lt in filters["analytic_tags"]])
            + ";  Analytic: "
            + ", ".join([at or "" for at in filters["analytics"]])
            + "; Operating Units: "
            + ", ".join([ou or "" for ou in filters["operating_units"]])
            + ";  Target Moves: "
            + filters.get("target_move").capitalize(),
            date_head,
        )

        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)

        row = 5
        col = 0

        row += 2
        if filters["debit_credit"] == "show":
            sheet.write(row, col, "", sub_heading)
            sheet.write(row, col + 1, "Debit", sub_heading)
            sheet.write(row, col + 2, "Credit", sub_heading)
        else:
            sheet.merge_range(
                "A{}:C{}".format(str(row + 1), str(row + 1)), "", sub_heading
            )
        sheet.write(row, col + 3, "Balance", sub_heading)

        if rl_data:
            for fr in rl_data:
                row += 1

                txt_name = workbook.add_format({"font_size": "10px", "border": 1})
                txt_name.set_indent(fr["level"] - 1)

                if filters["debit_credit"] == "show":
                    if fr["level"] == 1:
                        sheet.write(row, col, fr["name"], side_heading_main)
                    elif fr["level"] == 2:
                        sheet.write(row, col, fr["name"], side_heading_sub)
                    else:
                        sheet.write(row, col, fr["name"], txt_name)
                    sheet.write(row, col + 1, fr["debit"], txt)
                    sheet.write(row, col + 2, fr["credit"], txt)
                else:
                    if fr["level"] == 1:
                        sheet.merge_range(
                            "A{}:C{}".format(str(row + 1), str(row + 1)),
                            fr["name"],
                            side_heading_main,
                        )
                    elif fr["level"] == 2:
                        sheet.merge_range(
                            "A{}:C{}".format(str(row + 1), str(row + 1)),
                            fr["name"],
                            side_heading_sub,
                        )
                    else:
                        sheet.merge_range(
                            "A{}:C{}".format(str(row + 1), str(row + 1)),
                            fr["name"],
                            txt_name,
                        )
                sheet.write(row, col + 3, fr["balance"], txt)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
