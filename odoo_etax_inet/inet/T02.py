def prepare_data(doc, form_type, form_name):
    currency_code = doc.currency_id.name
    data = {
        "auto_submit": 1,
        "pdf_content": "",
        "form_type": form_type,
        "form_name": form_name,
    }
    control = {
        "c01_seller_tax_id": doc.company_id.vat or "",
        "c02_seller_branch_id": (
            "00000"
            if (
                not doc.company_id.branch
                or doc.company_id.branch.lower() in ["head office", "สำนักงานใหญ่"]
            )
            else doc.company_id.branch or ""
        ),
        "c03_file_name": "",
    }
    header = {
        "h01_document_type_code": doc.etax_doctype or "",
        "h02_document_name": dict(doc._fields["etax_doctype"].selection).get(
            doc.etax_doctype
        )
        or "",
        "h03_document_id": doc.name or "",
        "h04_document_issue_dtm": doc.invoice_date
        and doc.invoice_date.strftime("%Y-%m-%dT%H:%M:%S")
        or "",
        "h05_create_purpose_code": "",
        "h06_create_purpose": "",
        "h07_additional_ref_assign_id": "",
        "h08_additional_ref_issue_dtm": "",
        "h09_additional_ref_type_code": "",
        "h10_additional_ref_document_name": "",
        "h11_delivery_type_code": "",
        "h12_buyer_order_assign_id": "",
        "h13_buyer_order_issue_dtm": "",
        "h14_buyer_order_ref_type_code": "",
        "h15_document_remark": "",
        "h16_voucher_no": "",
        "h17_seller_contact_person_name": "",
        "h18_seller_contact_department_name": "",
        "h19_seller_contact_uriid": "",
        "h20_seller_contact_phone_no": "",
        "h21_flex_field": "",
        "h22_seller_branch_id": control.get("c02_seller_branch_id") or "",
        "h23_source_system": doc.env["ir.config_parameter"]
        .sudo()
        .get_param("web.base.url", ""),
        "h24_encrypt_password": "",  # password for pdf encryption
        "h25_pdf_template_id": "",  # ???
        "h26_send_mail_ind": "",  # ???
    }
    buyer = {
        "b01_buyer_id": "",
        "b02_buyer_name": doc.partner_id.name or "",
        "b03_buyer_tax_id_type": "TXID",  # ???
        "b04_buyer_tax_id": doc.partner_id.vat or "",
        "b05_buyer_branch_id": "00000"
        if (
            not doc.company_id.branch
            or doc.company_id.branch.lower() in ["head office", "สำนักงานใหญ่"]
        )
        else doc.company_id.branch or "",
        "b06_buyer_contact_person_name": "",
        "b07_buyer_contact_department_name": "",
        "b08_buyer_uriid": doc.partner_id.email or "",
        "b09_buyer_contact_phone_no": "",
        "b10_buyer_post_code": doc.partner_id.zip or "",
        "b11_buyer_building_name": "",
        "b12_buyer_building_no": "",
        "b13_buyer_address_line1": doc.partner_id.street or "",
        "b14_buyer_address_line2": doc.partner_id.street2 or "",
        "b15_buyer_address_line3": "",
        "b16_buyer_address_line4": "",
        "b17_buyer_address_line5": "",
        "b18_buyer_street_name": "",
        "b19_buyer_city_sub_div_id": "",
        "b20_buyer_city_sub_div_name": "",
        "b21_buyer_city_id": "",
        "b22_buyer_city_name": doc.partner_id.city or "",
        "b23_buyer_country_sub_div_id": "",
        "b24_buyer_country_sub_div_name": "",
        "b25_buyer_country_id": doc.partner_id.country_id
        and doc.partner_id.country_id.code
        or "",
    }
    lines = []
    i = 0
    for line in doc.invoice_line_ids.filtered(
        lambda l: not l.display_type and l.price_unit > 0
    ):
        i += 1
        lines.append(
            {
                "l01_line_id": i,
                "l02_product_id": line.product_id
                and line.product_id.default_code
                or "",
                "l03_product_name": line.product_id and line.product_id.name or "",
                "l04_product_desc": line.product_id.description or "",
                "l05_product_batch_id": "",
                "l06_product_expire_dtm": "",
                "l07_product_class_code": "",
                "l08_product_class_name": "",
                "l09_product_origin_country_id": "",
                "l10_product_charge_amount": line.price_unit,
                "l11_product_charge_currency_code": currency_code or "",
                "l12_product_allowance_charge_ind": "",
                "l13_product_allowance_actual_amount": "",
                "l14_product_allowance_actual_currency_code": currency_code or "",
                "l15_product_allowance_reason_code": "",
                "l16_product_allowance_reason": "",
                "l17_product_quantity": line.quantity or "",
                "l18_product_unit_code": "",  # ???
                "l19_product_quantity_per_unit": "",
                "l20_line_tax_type_code": line.tax_ids
                and "VAT"
                or "",  # ??? When to use Exempt?
                "l21_line_tax_cal_rate": line.tax_ids and line.tax_ids[0].amount or "",
                "l22_line_basis_amount": line.tax_ids and line.price_subtotal,
                "l23_line_basis_currency_code": currency_code or "",
                "l24_line_tax_cal_amount": line.price_total - line.price_subtotal,
                "l25_line_tax_cal_currency_code": currency_code or "",
                "l26_line_allowance_charge_ind": "",
                "l27_line_allowance_actual_amount": "",
                "l28_line_allowance_actual_currency_code": currency_code or "",
                "l29_line_allowance_reason_code": "",
                "l30_line_allowance_reason": "",
                "l31_line_tax_total_amount": line.price_total - line.price_subtotal,
                "l32_line_tax_total_currency_code": currency_code or "",
                "l33_line_net_total_amount": line.price_subtotal,
                "l34_line_net_total_currency_code": currency_code or "",
                "l35_line_net_include_tax_total_amount": line.price_total,
                "l36_line_net_include_tax_total_currency_code": currency_code or "",
                "l37_product_remark1": "",
                "l38_product_remark2": "",
                "l39_product_remark3": "",
                "l40_product_remark4": "",
                "l41_product_remark5": "",
                "l42_product_remark6": "",
                "l43_product_remark7": "",
                "l44_product_remark8": "",
                "l45_product_remark9": "",
                "l46_product_remark10": "",
            }
        )

    tax_groups = list(
        {
            (tax["l20_line_tax_type_code"], tax["l21_line_tax_cal_rate"])
            for tax in lines
            if tax["l20_line_tax_type_code"] and tax["l21_line_tax_cal_rate"] > 0
        }
    )  # list of (tax_code, rate)
    i = 0
    taxes = {}
    line_total = sum(line["l33_line_net_total_amount"] for line in lines)
    base_total = 0
    tax_total = 0
    for tax_group in tax_groups:
        i += 1
        tax_lines = list(
            filter(
                lambda l: (l["l20_line_tax_type_code"], l["l21_line_tax_cal_rate"])
                == tax_group,
                lines,
            )
        )
        base_amount = sum(line["l22_line_basis_amount"] for line in tax_lines)
        base_total += base_amount
        tax_amount = sum(line["l24_line_tax_cal_amount"] for line in tax_lines)
        tax_total += tax_amount
        taxes[i] = {
            "tax_code": tax_group[0],
            "tax_rate": tax_group[1],
            "base_amount": base_amount,
            "tax_amount": tax_amount,
        }

    footer = {
        "f01_line_total_count": len(lines),
        "f02_delivery_occur_dtm": "",
        "f03_invoice_currency_code": currency_code or "",
        # Tax 1
        "f04_tax_type_code1": taxes.get(1) and taxes[1]["tax_code"] or "",
        "f05_tax_cal_rate1": taxes.get(1) and taxes[1]["tax_rate"] or "",
        "f06_basis_amount1": taxes.get(1) and taxes[1]["base_amount"] or 0.00,
        "f07_basis_currency_code1": currency_code or "",
        "f08_tax_cal_amount1": taxes.get(1) and taxes[1]["tax_amount"] or 0.00,
        "f09_tax_cal_currency_code1": currency_code,
        # Tax 2
        "f10_tax_type_code2": taxes.get(2) and taxes[2]["tax_code"] or "",
        "f11_tax_cal_rate2": taxes.get(2) and taxes[2]["tax_rate"] or "",
        "f12_basis_amount2": taxes.get(2) and taxes[2]["base_amount"] or 0.00,
        "f13_basis_currency_code2": currency_code or "",
        "f14_tax_cal_amount2": taxes.get(2) and taxes[2]["tax_amount"] or 0.00,
        "f15_tax_cal_currency_code2": currency_code,
        # Tax 3
        "f16_tax_type_code3": taxes.get(3) and taxes[3]["tax_code"] or "",
        "f17_tax_cal_rate3": taxes.get(3) and taxes[3]["tax_rate"] or "",
        "f18_basis_amount3": taxes.get(3) and taxes[3]["base_amount"] or 0.00,
        "f19_basis_currency_code3": currency_code or "",
        "f20_tax_cal_amount3": taxes.get(3) and taxes[3]["tax_amount"] or 0.00,
        "f21_tax_cal_currency_code3": currency_code,
        # Tax 4
        "f22_tax_type_code4": taxes.get(3) and taxes[3]["tax_code"] or "",
        "f23_tax_cal_rate4": taxes.get(3) and taxes[3]["tax_rate"] or "",
        "f24_basis_amount4": taxes.get(3) and taxes[3]["base_amount"] or 0.00,
        "f25_basis_currency_code4": currency_code or "",
        "f26_tax_cal_amount4": taxes.get(3) and taxes[3]["tax_amount"] or 0.00,
        "f27_tax_cal_currency_code4": currency_code,
        # Allowance / Charge
        "f28_allowance_charge_ind": "",
        "f29_allowance_actual_amount": "",
        "f30_allowance_actual_currency_code": currency_code or "",
        "f31_allowance_reason_code": "",
        "f32_allowance_reason": "",
        "f33_payment_type_code": "",
        "f34_payment_description": "",
        "f35_payment_due_dtm": "",
        "f36_original_total_amount": "",
        "f37_original_total_currency_code": currency_code or "",
        "f38_line_total_amount": line_total,
        "f39_line_total_currency_code": currency_code or "",
        "f40_adjusted_information_amount": "",
        "f41_adjusted_information_currency_code": currency_code or "",
        "f42_allowance_total_amount": "",
        "f43_allowance_total_currency_code": currency_code or "",
        "f44_charge_total_amount": "",
        "f45_charge_total_currency_code": currency_code or "",
        "f46_tax_basis_total_amount": base_total,
        "f47_tax_basis_total_currency_code": currency_code or "",
        "f48_tax_total_amount": tax_total,
        "f49_tax_total_currency_code": currency_code or "",
        "f50_grand_total_amount": line_total + tax_total,
        "f51_grand_total_currency_code": currency_code or "",
        "f52_term_payment": "",
        "f53_withholdingtax_type1": "",
        "f54_withholdingtax_description1": "",
        "f55_withholdingtax_rate1": "",
        "f56_withholdingtax_basis_amount1": "",
        "f57_withholdingtax_tax_amount1": "",
        "f58_withholdingtax_type2": "",
        "f59_withholdingtax_description2": "",
        "f60_withholdingtax_rate2": "",
        "f61_withholdingtax_basis_amount2": "",
        "f62_withholdingtax_tax_amount2": "",
        "f63_withholdingtax_type3": "",
        "f64_withholdingtax_description3": "",
        "f65_withholdingtax_rate3": "",
        "f66_withholdingtax_basis_amount3": "",
        "f67_withholdingtax_tax_amount3": "",
        "f68_withholdingtax_total_amount": "",
        "f69_actual_payment_total_amount": "",
        "f70_document_remark1": "",
        "f71_document_remark2": "",
        "f72_document_remark3": "",
        "f73_document_remark4": "",
        "f74_document_remark5": "",
        "f75_document_remark6": "",
        "f76_document_remark7": "",
        "f77_document_remark8": "",
        "f78_document_remark9": "",
        "f79_document_remark10": "",
        "t01_total_document_count": "1",
    }
    data.update(control)
    data.update(header)
    data.update(buyer)
    data.update({"line_item_information": lines})
    data.update(footer)
    return data
