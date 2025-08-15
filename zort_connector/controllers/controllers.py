# -*- coding: utf-8 -*-
from odoo import http


class ZortConnector(http.Controller):
    @http.route('/zort_connector/zort_connector', auth='public')
    def index(self, **kw):
        return "Hello, world"

#     @http.route('/zort_connector/zort_connector/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zort_connector.listing', {
#             'root': '/zort_connector/zort_connector',
#             'objects': http.request.env['zort_connector.zort_connector'].search([]),
#         })

#     @http.route('/zort_connector/zort_connector/objects/<model("zort_connector.zort_connector"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zort_connector.object', {
#             'object': obj
#         })

