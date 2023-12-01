# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import json
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from ..inet import inet_data_template as data_template

_logger = logging.getLogger(__name__)

# TODO:
# - If processing or success, do not allow sent again.
# - Job to push and pull latest information (if processing)

ETAX_SYSTEMS = ["INET ETax Document"]


class ETaxTH(models.AbstractModel):
    _name = "etax.th"
    _description = "ETax Abstract Model"

    etax_doctype = fields.Selection(
        selection=[
            # ("380", "ใบแจ้งหนี้"),
            ("388", "ใบกํากับภาษี"),
            ("T02", "ใบแจ้งหนี้/ใบกํากับภาษี"),
            ("T03", "ใบเสร็จรับเงิน/ใบกํากับภาษี"),
            ("T04", "ใบส่งของ/ใบกํากับภาษี"),
            ("T05", "ใบกํากับภาษี อย่างย่อ"),
            ("T01", "ใบรับ (ใบเสร็จรับเงิน)"),
            ("80", "ใบเพิมหนี้"),
            ("81", "ใบลดหนี้"),
        ],
        string="eTax Doctype",
        copy=False,
    )
    etax_status = fields.Selection(
        selection=[
            ("success", "Success"),
            ("error", "Error"),
            ("processing", "Processing"),
            ("to_process", "To Process"),
        ],
        string="ETax Status",
        readonly=False,
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
    replaced_entry_id = fields.Many2one(
        comodel_name="account.move",
        string="Replaced Document",
        readonly=True,
        copy=False,
    )
    is_send_frappe = fields.Boolean(
        copy=False,
    )
    doc_name_template = fields.Many2one(
        string="Invoice template",
        comodel_name="doc.type",
        copy=False,
    )

    def _update_field_url(self):
        return [
            "status",
            "transaction_code",
            "error_code",
            "error_message",
            "pdf_url",
            "xml_url",
        ]

    def update_processing_document(self):
        self.ensure_one()
        if self.etax_status != "processing":
            return
        auth_token, server_url = self._get_connection()
        url = (
            '%s/api/resource/%s?filters=[["transaction_code","=","%s"]]'
            "&fields=%s"
            % (
                server_url,
                "INET ETax Document",
                self.etax_transaction_code,
                self._update_field_url(),
            )
        )
        res = requests.get(
            url,
            headers={"Authorization": "token %s" % auth_token},
            timeout=20,
        ).json()
        if not res.get("data"):
            return
        response = res.get("data")[0]
        # Update status
        self.etax_status = response.get("status").lower()
        self.etax_error_code = response.get("error_code")
        self.etax_error_message = response.get("error_message")
        if self.etax_status == "success":
            pdf_url, xml_url = [response.get("pdf_url"), response.get("xml_url")]
            if pdf_url:
                self.env["ir.attachment"].create(
                    {
                        "name": "%s_signed.pdf" % self.name,
                        "datas": base64.b64encode(requests.get(pdf_url).content),
                        "type": "binary",
                        "res_model": "account.move",
                        "res_id": self.id,
                    }
                )
            if xml_url:
                self.env["ir.attachment"].create(
                    {
                        "name": "%s_signed.xml" % self.name,
                        "datas": base64.b64encode(requests.get(xml_url).content),
                        "type": "binary",
                        "res_model": "account.move",
                        "res_id": self.id,
                    }
                )

    def run_update_processing_document(self):
        """This method is called from a cron job.
        It is used to update processing documents
        """
        records = self.search([("etax_status", "=", "processing")])
        for record in records:
            try:
                record.update_processing_document()
                self._cr.commit()
            except Exception as e:
                _logger.warning(e)

    def sign_etax(self):
        self.ensure_one()
        # Prepare data
        form_type = self.doc_name_template.doc_source_template or False
        form_name = self.doc_name_template.name or False
        self._pre_validation(form_type, form_name)
        pdf_content = self._get_odoo_form(form_type, form_name)
        doc_data = data_template.prepare_data(self)  # Rest API
        self._send_to_frappe(doc_data, form_type, form_name, pdf_content)

    def run_sign_etax(self):
        """This method is called from a cron job.
        It is used to sign etax for document with status "to_process"
        """
        records = self.search([("etax_status", "=", "to_process")])
        for record in records:
            try:
                record.sign_etax()
            except Exception as e:
                record.etax_error_message = str(e)
            self._cr.commit()

    def _pre_validation(self, form_type, form_name):
        self.ensure_one()
        if form_type not in ["odoo", "frappe"]:
            raise ValidationError(_("Form Type not in ['odoo', 'frappe']"))
        if form_type and not form_name:
            raise ValidationError(
                _("form_name is not specified for form_type=%s") % form_type
            )

    def _get_connection(self):
        auth_token = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("frappe_etax_service.frappe_auth_token")
        )
        server_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("frappe_etax_service.frappe_server_url")
        )
        if not auth_token or not server_url:
            raise ValidationError(
                "Cannot connect to Frappe Server.\n"
                "Frappe Server URL or Frappe Auth Token are not defined."
            )
        return (auth_token, server_url)

    def _get_odoo_form(self, form_type, form_name):
        if form_type == "odoo":
            report = self.env["ir.actions.report"].search([("name", "=", form_name)])
            if len(report) != 1:
                raise ValidationError(_("Cannot find form - %s") % form_name)
            content, content_type = report._render_qweb_pdf(self.id)
            return base64.b64encode(content).decode()
        return ""

    def _send_to_frappe(self, doc_data, form_type, form_name, pdf_content):
        auth_token, server_url = self._get_connection()
        try:
            res = requests.post(
                url="%s/api/method/%s"
                % (server_url, "etax_inet.api.etax.sign_etax_document"),
                headers={"Authorization": "token %s" % auth_token},
                data={
                    "doc_data": json.dumps(doc_data),
                    "form_type": form_type,  # odoo or frappe
                    "form_name": form_name,  # odoo's report name or frappe's print format
                    "pdf_content": pdf_content,
                },
                timeout=20,
            ).json()
            response = res.get("message")
            if not response:  # Can't create record on Frappe
                self.etax_status = "error"
                self.etax_error_message = res.get(
                    "exception", res.get("_server_messages")
                )
                return
            # Update status
            self.etax_status = response.get("status").lower()
            self.etax_transaction_code = response.get("transaction_code")
            self.etax_error_code = response.get("error_code")
            self.etax_error_message = response.get("error_message")
            # Get signed document back
            if self.etax_status == "success":
                pdf_url, xml_url = [response.get("pdf_url"), response.get("xml_url")]
                if pdf_url:
                    self.env["ir.attachment"].create(
                        {
                            "name": "%s_signed.pdf" % self.name,
                            "datas": base64.b64encode(requests.get(pdf_url).content),
                            "type": "binary",
                            "res_model": "account.move",
                            "res_id": self.id,
                        }
                    )
                if xml_url:
                    self.env["ir.attachment"].create(
                        {
                            "name": "%s_signed.xml" % self.name,
                            "datas": base64.b64encode(requests.get(xml_url).content),
                            "type": "binary",
                            "res_model": "account.move",
                            "res_id": self.id,
                        }
                    )
        except Exception as e:
            self.etax_status = "error"
            self.etax_error_message = str(e)
