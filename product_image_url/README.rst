Product Image from URL
======================

Adds an ``Image URL`` field to products. Creating a product with a URL, or
changing an existing URL, downloads the image and stores it in Odoo's standard
``image_1920`` field. The URL is an import source only; product images are never
served directly from an external host.

The maximum width and height of downloaded images can be configured under
General Settings as 512, 1024, or 1920 pixels. The default is 1024 pixels and
the setting applies only to future downloads. Odoo's standard image mixin then
provides the usual ``image_1024``, ``image_512``, ``image_256``, and
``image_128`` fields.

The downloader validates redirects, rejects private network destinations,
requires an image response, and limits downloads to 10 MB. Clearing the URL
does not delete an image that has already been downloaded.

When upgrading from a version that supported external URL mode, set or import
the URL again for products that do not already have a stored image. The module
upgrade intentionally does not contact remote image servers.

Do not install this module together with another module that defines the same
``product.template.image_url`` field, such as the legacy ``product_import``
module in this repository.
