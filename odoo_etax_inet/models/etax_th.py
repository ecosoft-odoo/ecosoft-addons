# Copyright 2023 Kitti U.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from ..inet import T02

# TODO:
# - If processing or success, do not allow sent again.
# - Job to push and pull latest information (if processing)

ETAX_SYSTEMS = ["INET ETax Document"]


class ETaxTH(models.AbstractModel):
    _name = "etax.th"
    _description = "ETax Abstract Model"

    etax_doctype = fields.Selection(
        selection=[
            ("380", "ใบแจ้งหนี้"),
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

    def sign_etax(self, form_type=False, form_name=False):
        self._pre_validation(form_type, form_name)
        print("=" * 100)
        print(f"form type- {form_type}\nform name- {form_name}")
        print("_pre_validation is successed.")
        # x=1/0
        auth_token, server_url = self._get_connection()
        doc = self._prepare_inet_data(form_type=form_type, form_name=form_name)
        print("=" * 30)
        self._prepare_odoo_pdf(doc, form_name)
        print(type(doc))
        print("_prepare_odoo_pdf() is successed.")
        self._send_to_frappe(doc, server_url, auth_token)

    def _pre_validation(self, form_type, form_name):
        self.ensure_one()
        if form_type not in ["odoo", "frappe"]:
            raise ValidationError(_("Form Type not in ['odoo', 'frappe']"))
        if form_type and not form_name:
            raise ValidationError(
                _("form_name is not specified for form_type=%s") % form_type
            )

    def _prepare_inet_data(self, form_type="", form_name=""):
        self.ensure_one()
        data = {}
        if self.etax_doctype == "T02":
            data = T02.prepare_data(self, form_type, form_name)
        else:
            raise ValidationError(_("No etax_doctype"))
        return data

    def _get_connection(self):
        auth_token = (
            self.env["ir.config_parameter"].sudo().get_param("frappe.auth.token")
        )
        server_url = (
            self.env["ir.config_parameter"].sudo().get_param("frappe.server.url")
        )
        if not auth_token or not server_url:
            raise ValidationError(
                    "Cannot connect to Frappe Server.\n"
                    "System parameters frappe.server.url, frappe.auth.token not found"
            )
        return (auth_token, server_url)

    def _prepare_odoo_pdf(self, doc, form_name):
        if doc["form_type"] == "odoo":
            report = self.env["ir.actions.report"].search([("name", "=", form_name)])
            if len(report) != 1:
                raise ValidationError(_("Cannot find form - %s") % form_name)
            content, content_type = report._render_qweb_pdf(self.id)
            doc["pdf_content"] = base64.b64encode(content).decode()

    def _send_to_frappe(self, doc, server_url, auth_token):
        return True
        # res = requests.post(
        #     url="%s/api/resource/%s" % (server_url, "INET ETax Document"),
        #     headers={"Authorization": "token %s" % auth_token},
        #     data=json.dumps(doc),
        #     timeout=10,
        # ).json()

        # response = res.get("data")
        # if not response:
        #     self.etax_status = "error"
        #     self.etax_error_message = res.get("exception", res.get("_server_messages"))
        #     return
        # # Update status
        # self.etax_status = response.get("status").lower()
        # self.etax_transaction_code = response.get("transaction_code")
        # self.etax_error_code = response.get("error_code")
        # self.etax_error_message = response.get("error_message")
        # # Get signed document back
        # if self.etax_status == "success":
        #     for url in [response.get("pdf_url"), response.get("pdf_url")]:
        #         if not url:
        #             continue
        #         self.env["ir.attachment"].create({
        #             "name": "%s_signed.pdf" % self.name,
        #             "datas": base64.b64encode(requests.get(url).content),
        #             "type": "binary",
        #             "res_model": "account.move",
        #             "res_id": self.id,
        #         })
