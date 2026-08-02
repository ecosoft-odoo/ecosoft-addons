# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.image import image_process


class ProductTemplate(models.Model):
    _inherit = "product.template"

    _IMAGE_DOWNLOAD_MAX_BYTES = 10 * 1024 * 1024
    _IMAGE_DOWNLOAD_MAX_REDIRECTS = 5
    _IMAGE_DOWNLOAD_TIMEOUT = (5, 20)
    _IMAGE_MAX_SIZES = (512, 1024, 1920)
    _IMAGE_DOWNLOAD_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    )

    image_url = fields.Char(
        string="Image URL",
        copy=False,
        help=(
            "HTTP or HTTPS URL used to download the product image into Odoo. "
            "Changing the URL downloads and replaces the stored image."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._normalize_image_url_vals(vals) for vals in vals_list]
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list, strict=False):
            if vals.get("image_url"):
                record._download_and_store_image_url()
        return records

    def write(self, vals):
        vals = self._normalize_image_url_vals(vals)
        result = super().write(vals)
        if vals.get("image_url"):
            for record in self:
                record._download_and_store_image_url()
        return result

    @api.model
    def _get_configured_image_max_size(self):
        configured_size = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("product_image_url.max_size", "1024")
        )
        try:
            size = int(configured_size)
        except (TypeError, ValueError):
            return 1024
        return size if size in self._IMAGE_MAX_SIZES else 1024

    @api.model
    def _normalize_image_url_vals(self, vals):
        if "image_url" not in vals:
            return vals
        vals = dict(vals)
        vals["image_url"] = (vals.get("image_url") or "").strip() or False
        return vals

    def _download_and_store_image_url(self):
        self.ensure_one()
        image_content = self._download_image_url(self.image_url)
        max_size = self._get_configured_image_max_size()
        processed_image = image_process(
            image_content,
            size=(max_size, max_size),
            verify_resolution=True,
        )
        self.image_1920 = base64.b64encode(processed_image)

    @api.model
    def _download_image_url(self, url):
        current_url = url
        session = requests.Session()
        try:
            for redirect_count in range(self._IMAGE_DOWNLOAD_MAX_REDIRECTS + 1):
                self._validate_public_image_url(current_url)
                parsed_url = urlsplit(current_url)
                headers = {
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                    "Referer": f"{parsed_url.scheme}://{parsed_url.netloc}/",
                    "User-Agent": self._IMAGE_DOWNLOAD_USER_AGENT,
                }
                try:
                    response = session.get(
                        current_url,
                        allow_redirects=False,
                        headers=headers,
                        stream=True,
                        timeout=self._IMAGE_DOWNLOAD_TIMEOUT,
                    )
                except requests.RequestException as error:
                    raise UserError(
                        self.env._("Could not download the product image: %s") % error
                    ) from error

                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get("Location")
                    response.close()
                    if not location:
                        raise UserError(
                            self.env._("The image server returned an invalid redirect.")
                        )
                    if redirect_count == self._IMAGE_DOWNLOAD_MAX_REDIRECTS:
                        raise UserError(
                            self.env._("The image URL has too many redirects.")
                        )
                    current_url = urljoin(current_url, location)
                    continue

                try:
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "")
                    content_type = content_type.split(";", 1)[0].strip().lower()
                    if not content_type.startswith("image/"):
                        raise UserError(
                            self.env._(
                                "The URL did not return an image (Content-Type: %s)."
                            )
                            % (content_type or self.env._("unknown"))
                        )

                    content_length = response.headers.get("Content-Length")
                    if (
                        content_length
                        and int(content_length) > self._IMAGE_DOWNLOAD_MAX_BYTES
                    ):
                        raise UserError(self._image_too_large_message())

                    content = bytearray()
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        content.extend(chunk)
                        if len(content) > self._IMAGE_DOWNLOAD_MAX_BYTES:
                            raise UserError(self._image_too_large_message())
                except requests.RequestException as error:
                    raise UserError(
                        self.env._("Could not download the product image: %s") % error
                    ) from error
                except (TypeError, ValueError) as error:
                    raise UserError(
                        self.env._("The image server returned an invalid response.")
                    ) from error
                finally:
                    response.close()

                return bytes(content)
        finally:
            session.close()

        raise UserError(self.env._("Could not download the product image."))

    @api.model
    def _validate_public_image_url(self, url):
        parsed_url = urlsplit(url)
        if parsed_url.scheme not in ("http", "https"):
            raise ValidationError(self.env._("The image URL must use HTTP or HTTPS."))
        if not parsed_url.hostname or parsed_url.username or parsed_url.password:
            raise ValidationError(self.env._("The image URL is not valid."))

        try:
            port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
            addresses = socket.getaddrinfo(
                parsed_url.hostname, port, type=socket.SOCK_STREAM
            )
        except (OSError, ValueError) as error:
            raise ValidationError(
                self.env._("The image URL host could not be resolved.")
            ) from error

        if not addresses:
            raise ValidationError(
                self.env._("The image URL host could not be resolved.")
            )
        for address in addresses:
            ip_address = ipaddress.ip_address(address[4][0])
            if not ip_address.is_global:
                raise ValidationError(
                    self.env._("The image URL must point to a public host.")
                )

    @api.model
    def _image_too_large_message(self):
        max_size_mb = self._IMAGE_DOWNLOAD_MAX_BYTES // (1024 * 1024)
        return self.env._("The image is larger than the allowed %s MB.") % max_size_mb
