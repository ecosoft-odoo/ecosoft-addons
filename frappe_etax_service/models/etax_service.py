# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import json
import logging

import requests

from odoo import fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

FRAPPE_ETAX_API_CODES = {
    "FRAPPE_ETAX_SIGN",
    "FRAPPE_ETAX_PAYMENT_SIGN",
    "FRAPPE_ETAX_PAYMENT_REPLACE",
}


class ETaxServiceMixin(models.AbstractModel):
    _name = "etax.service.mixin"
    _inherit = "common.base.api"
    _description = "ETax Service Model"

    etax_doctype_id = fields.Many2one(
        string="eTax Doctype",
        comodel_name="etax.doctype",
        copy=False,
    )
    etax_doctype_code = fields.Char(
        related="etax_doctype_id.doctype_code_id.code",
        store=True,
        string="eTax Doctype Code",
    )
    etax_status = fields.Selection(
        selection=[
            ("success", "Success"),
            ("replace", "Replaced"),
            ("error", "Error"),
            ("processing", "Processing"),
        ],
        string="ETax Status",
        copy=False,
    )
    etax_error_code = fields.Char(
        copy=False,
    )
    etax_error_message = fields.Text(
        copy=False,
    )
    etax_transaction_code = fields.Char(
        copy=False,
    )
    create_purpose_code = fields.Char(
        copy=False,
    )
    create_purpose = fields.Char(
        copy=False,
    )
    is_send_frappe = fields.Boolean(
        copy=False,
    )

    def _get_odoo_form(self):
        report = self.etax_doctype_id.report_id
        content, _ = report._render_qweb_pdf(report.xml_id, res_ids=self.ids)
        return base64.b64encode(content).decode()

    def _get_payload_globals_dict(self):
        globals_dict = super()._get_payload_globals_dict()
        form_type = self.etax_doctype_id.doc_source_template or False
        form_name = self.etax_doctype_id.name or False
        return {
            **globals_dict,
            "form_type": form_type,
            "form_name": form_name,
            "pdf_content": self._get_odoo_form() if form_type == "odoo" else False,
        }

    def _get_frappe_etax_connection(self):
        self.ensure_one()
        company = self.company_id
        connection = company.sudo().frappe_etax_connection_id
        if not connection:
            raise ValidationError(
                self.env._("Company '%s' does not have a Frappe e-Tax Connection.")
                % company.display_name
            )
        connection = connection.sudo()
        if connection.company_id != company:
            raise ValidationError(
                self.env._("The Frappe e-Tax Connection must belong to company '%s'.")
                % company.display_name
            )
        if not connection.active:
            raise ValidationError(
                self.env._("Frappe e-Tax Connection '%s' is archived.")
                % connection.display_name
            )
        return connection

    def _execute_rest_api(self, api_data, auth_token, payload=None, params=None):
        if api_data.code not in FRAPPE_ETAX_API_CODES:
            return super()._execute_rest_api(
                api_data, auth_token, payload=payload, params=params
            )

        connection = self._get_frappe_etax_connection()
        runtime_api_data = self.env["api.config"].new(
            {
                "endpoint_url": connection.server_url,
                "headers": api_data.headers,
                "is_form_data": api_data.is_form_data,
                "method": api_data.method,
                "route_path": api_data.route_path,
            }
        )
        return super()._execute_rest_api(
            runtime_api_data,
            connection.auth_token,
            payload=payload,
            params=params,
        )

    def _prepare_etax_payload(self):
        self.ensure_one()
        form_type = self.etax_doctype_id.doc_source_template or "odoo"
        form_name = self.etax_doctype_id.name or ""
        pdf_content = self._get_etax_pdf_content(form_type, form_name)
        doc_data = self._prepare_etax_doc_data()
        return {
            "doc_data": json.dumps(doc_data),
            "form_type": form_type,
            "form_name": form_name,
            "pdf_content": pdf_content,
        }

    def _get_etax_pdf_content(self, form_type, form_name):
        if form_type != "odoo" or not form_name:
            return ""
        report = self.env["ir.actions.report"].search([("name", "=", form_name)])
        if len(report) != 1:
            raise ValidationError(
                self.env._("Cannot find report '%s', or multiple found") % form_name
            )
        content, _ctype = report._render_qweb_pdf(report.xml_id, res_ids=self.ids)
        return base64.b64encode(content).decode()

    def _prepare_etax_doc_data(self):
        raise UserError(
            self.env._("_prepare_etax_doc_data() not implemented for model: %s")
            % self._name
        )

    def _hook_on_failed(self, code_api, error_msg):
        if code_api != self._etax_sign_api_code:
            return
        self.write(
            {
                "etax_status": "error",
                "etax_error_message": error_msg,
            }
        )

    def _hook_update_data(self, code_api, result):
        if code_api != self._etax_sign_api_code:
            return
        response = result.get("message") or {}
        self.write(
            {
                "etax_status": (response.get("status") or "").lower() or "success",
                "etax_transaction_code": response.get("transaction_code"),
                "etax_error_code": response.get("error_code"),
                "etax_error_message": response.get("error_message"),
            }
        )
        if self.etax_status == "success":
            for ext in ("pdf", "xml"):
                url = response.get(f"{ext}_url")
                if url:
                    self._attach_etax_document(url, ext)

    def _attach_etax_document(self, url, ext):
        content = requests.get(url, timeout=20).content
        self.env["ir.attachment"].create(
            {
                "name": f"{self.name}_signed.{ext}",
                "datas": base64.b64encode(content),
                "type": "binary",
                "res_model": self._name,
                "res_id": self.id,
            }
        )

    def _pre_etax_validate(self):
        disabled = self.filtered(
            lambda record: not record.company_id.is_etax_configured
        )
        if disabled:
            raise ValidationError(
                self.env._("e-Tax is not enabled for company '%s'.")
                % disabled[0].company_id.display_name
            )
        for record in self:
            record._get_frappe_etax_connection()

        invalid = self.filtered(
            lambda m: m.etax_status in ["success", "replace", "processing"]
        )
        if invalid:
            names = ", ".join(invalid.mapped("name"))
            raise ValidationError(
                self.env._("%s: eTax status is already Processing/Success") % names
            )
        # Posted for account.move, Paid for account.payment
        invalid = self.filtered(lambda m: m.state not in ["posted", "paid"])
        if invalid:
            names = ", ".join(invalid.mapped("name"))
            raise ValidationError(
                self.env._("%s: must be posted/paid before signing eTax") % names
            )
        if not self.company_id.vat:
            raise ValidationError(
                self.env._("Company '%s' does not have a Tax ID (VAT) configured.")
                % self.company_id.name
            )

    def _prepare_context_for_wizard(self, **kwargs):
        context = self.env.context.copy()
        context.update(**kwargs)
        return context

    def button_etax_invoices(self):
        self.ensure_one()
        context = self._prepare_context_for_wizard()
        return {
            "name": self.env._("Sign e-Tax Invoice"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "etax.doctype.wizard",
            "target": "new",
            "context": context,
        }
