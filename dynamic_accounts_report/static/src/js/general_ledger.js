odoo.define("dynamic_accounts_report.general_ledger", function (require) {
    "use strict";
    var AbstractAction = require("web.AbstractAction");
    var core = require("web.core");
    var rpc = require("web.rpc");
    var QWeb = core.qweb;

    var GeneralLedger = AbstractAction.extend({
        template: "GeneralTemp",
        events: {
            "click .gl-line": "show_drop_down",
            "click .view-account-move": "view_acc_move",
        },

        init: function (parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.report_lines = action.report_lines;
            this.wizard_id = action.context.wizard | null;
        },

        start: function () {
            var self = this;
            rpc.query({
                model: "account.general.ledger",
                method: "create",
                args: [{}],
                context: this.searchModel.config.context,
            }).then(function (t_res) {
                self.wizard_id = t_res;
                self.load_data();
            });
        },

        load_data: function () {
            var self = this;
            var action_title = self._title;
            try {
                self._rpc({
                    model: "account.general.ledger",
                    method: "view_report",
                    args: [[self.wizard_id], action_title],
                    context: {active_test: false},
                }).then(function (datas) {
                    _.each(datas.report_lines, function (rep_lines) {
                        rep_lines.debit = self.format_currency(
                            datas.currency,
                            rep_lines.debit
                        );
                        rep_lines.credit = self.format_currency(
                            datas.currency,
                            rep_lines.credit
                        );
                        rep_lines.balance = self.format_currency(
                            datas.currency,
                            rep_lines.balance
                        );
                    });

                    self.$(".table_view_tb").html(
                        QWeb.render("GLTable", {
                            report_lines: datas.report_lines,
                            filter: datas.filters,
                            currency: datas.currency,
                            credit_total: datas.credit_total,
                            debit_total: datas.debit_total,
                            debit_balance: datas.debit_balance,
                        })
                    );
                });
            } catch (el) {
                console.log(el);
            }
        },

        format_currency: function (currency, amount) {
            if (typeof amount !== "number") {
                amount = parseFloat(amount);
            }
            var formatted_value = parseInt(amount).toLocaleString(currency[2], {
                minimumFractionDigits: 2,
            });
            return formatted_value;
        },

        show_drop_down: function (event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data("account-id");
            var td = $(event.currentTarget).next("tr").find("td");
            if (td.length === 1) {
                var action_title = self._title;
                self._rpc({
                    model: "account.general.ledger",
                    method: "view_report",
                    args: [[self.wizard_id], action_title],
                    context: {active_test: false},
                }).then(function (data) {
                    _.each(data.report_lines, function (rep_lines) {
                        _.each(rep_lines.move_lines, function (move_line) {
                            move_line.debit = self.format_currency(
                                data.currency,
                                move_line.debit
                            );
                            move_line.credit = self.format_currency(
                                data.currency,
                                move_line.credit
                            );
                            move_line.balance = self.format_currency(
                                data.currency,
                                move_line.balance
                            );
                        });
                    });

                    for (var i = 0; i < data.report_lines.length; i++) {
                        if (account_id === data.report_lines[i].id) {
                            $(event.currentTarget)
                                .next("tr")
                                .find("td .gl-table-div")
                                .remove();
                            $(event.currentTarget)
                                .next("tr")
                                .find("td ul")
                                .after(
                                    QWeb.render("SubSection", {
                                        account_data: data.report_lines[i].move_lines,
                                        currency_symbol: data.currency[0],
                                        currency_position: data.currency[1],
                                    })
                                );
                            $(event.currentTarget)
                                .next("tr")
                                .find("td ul li:first a")
                                .css({
                                    "background-color": "#00ede8",
                                    "font-weight": "bold",
                                });
                        }
                    }
                });
            }
        },

        view_acc_move: function (event) {
            event.preventDefault();
            var self = this;
            var context = {};
            var show_acc_move = function (res_model, res_id, view_id) {
                var action = {
                    type: "ir.actions.act_window",
                    view_type: "form",
                    view_mode: "form",
                    res_model: res_model,
                    views: [[view_id || false, "form"]],
                    res_id: res_id,
                    target: "current",
                    context: context,
                };
                return self.do_action(action);
            };
            rpc.query({
                model: "account.move",
                method: "search_read",
                domain: [["id", "=", $(event.currentTarget).data("move-id")]],
                fields: ["id"],
                limit: 1,
            }).then(function (record) {
                if (record.length > 0) {
                    show_acc_move("account.move", record[0].id);
                } else {
                    show_acc_move(
                        "account.move",
                        $(event.currentTarget).data("move-id")
                    );
                }
            });
        },
    });
    core.action_registry.add("g_l", GeneralLedger);
    return GeneralLedger;
});
