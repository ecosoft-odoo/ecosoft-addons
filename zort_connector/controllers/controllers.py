from odoo import http
from odoo.http import Response, request


class ZortConnector(http.Controller):
    @http.route("/zort_connector/zort_connector", auth="public")
    def index(self, **kw):
        return "Hello, world"

    @http.route(
        "/zort_connector/view_zort_order_json/<int:sale_order_id>",
        type="http",
        auth="user",
    )
    def view_zort_order_json(self, sale_order_id, **kwargs):
        sale_order = request.env["sale.order"].sudo().browse(sale_order_id)
        if not sale_order.exists():
            return Response("Sale Order not found", status=404)
        import json

        return Response(
            json.dumps(sale_order.zort_order_data, indent=2, ensure_ascii=False),
            mimetype="application/json",
        )
