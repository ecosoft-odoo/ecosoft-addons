from odoo import http


class ZortConnector(http.Controller):
    @http.route("/zort_connector/zort_connector", auth="public")
    def index(self, **kw):
        return "Hello, world"
