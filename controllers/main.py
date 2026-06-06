from odoo import http
from odoo.http import request


class ItParcController(http.Controller):

    @http.route('/it_parc/dashboard_data', type='json', auth='user')
    def dashboard_data(self):
        return request.env['it.equipement'].get_dashboard_data()
