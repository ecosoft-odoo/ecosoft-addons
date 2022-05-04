# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models

from ...auditlog.models.rule import EMPTY_DICT, DictDiffer


class AuditlogRule(models.Model):
    _inherit = "auditlog.rule"

    def create_logs(
        self,
        uid,
        res_model,
        res_ids,
        method,
        old_values=None,
        new_values=None,
        additional_log_values=None,
    ):
        if res_model == "mis.budget.item":
            if old_values is None:
                old_values = EMPTY_DICT
            if new_values is None:
                new_values = EMPTY_DICT
            log_model = self.env["auditlog.log"]
            http_request_model = self.env["auditlog.http.request"]
            http_session_model = self.env["auditlog.http.session"]
            model_model = self.env[res_model]
            for res_id in res_ids:
                name = model_model.browse(res_id).name_get()
                model_id = self.pool._auditlog_model_cache[res_model]
                auditlog_rule = self.env["auditlog.rule"].search(
                    [("model_id", "=", model_id)]
                )
                # Overwrite name for mis.budget.item only (date range / name)
                date_range_name = model_model.browse(res_id).date_range_id.name
                analytic_name = model_model.browse(
                    res_id
                ).analytic_account_id.display_name
                res_name = name and name[0] and name[0][1]
                vals = {
                    "name": _("{} / {}".format(date_range_name, res_name)),
                    "model_id": self.pool._auditlog_model_cache[res_model],
                    "res_id": res_id,
                    "method": method,
                    "user_id": uid,
                    "http_request_id": http_request_model.current_http_request(),
                    "http_session_id": http_session_model.current_http_session(),
                    "ref": analytic_name,
                }
                vals.update(additional_log_values or {})
                log = log_model.create(vals)
                diff = DictDiffer(
                    new_values.get(res_id, EMPTY_DICT),
                    old_values.get(res_id, EMPTY_DICT),
                )
                if method == "create":
                    self._create_log_line_on_create(log, diff.added(), new_values)
                elif method == "read":
                    self._create_log_line_on_read(
                        log, list(old_values.get(res_id, EMPTY_DICT).keys()), old_values
                    )
                elif method == "write":
                    self._create_log_line_on_write(
                        log, diff.changed(), old_values, new_values
                    )
                elif method == "unlink" and auditlog_rule.capture_record:
                    self._create_log_line_on_read(
                        log, list(old_values.get(res_id, EMPTY_DICT).keys()), old_values
                    )
            return
        return super().create_logs(
            uid,
            res_model,
            res_ids,
            method,
            old_values,
            new_values,
            additional_log_values,
        )
