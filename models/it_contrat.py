import base64
import io
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class ItContrat(models.Model):
    _name = 'it.contrat'
    _description = 'Contrat fournisseur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_fin'

    name = fields.Char(string='Référence contrat', required=True, tracking=True)
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', required=True, tracking=True, ondelete='restrict')
    type_contrat = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('licence', 'Licence'),
        ('support', 'Support'),
    ], string='Type de contrat', required=True, default='maintenance', tracking=True)

    date_debut = fields.Date(string='Date de début', required=True, tracking=True)
    date_fin = fields.Date(string='Date de fin', required=True, tracking=True)
    montant = fields.Float(string='Montant (FCFA)', digits=(16, 0), tracking=True)

    equipement_ids = fields.Many2many(
        'it.equipement',
        'it_contrat_equipement_rel',
        'contrat_id', 'equipement_id',
        string='Équipements couverts',
    )

    jours_restants = fields.Integer(compute='_compute_jours_restants', search='_search_jours_restants', string='Jours restants', store=False)
    state = fields.Selection([
        ('actif', 'Actif'),
        ('expire', 'Expiré'),
        ('renouvele', 'Renouvelé'),
    ], string='État', default='actif', tracking=True)

    description = fields.Text(string='Notes')

    def _search_jours_restants(self, operator, value):
        today = fields.Date.today()
        if operator == '<=':
            return [('date_fin', '>=', today), ('date_fin', '<=', today + timedelta(days=value))]
        if operator == '<':
            return [('date_fin', '>=', today), ('date_fin', '<=', today + timedelta(days=value - 1))]
        if operator == '>=':
            return [('date_fin', '>=', today + timedelta(days=value))]
        if operator == '>':
            return [('date_fin', '>=', today + timedelta(days=value + 1))]
        if operator == '=':
            return [('date_fin', '=', today + timedelta(days=value))]
        return []

    @api.depends('date_fin')
    def _compute_jours_restants(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_fin:
                rec.jours_restants = (rec.date_fin - today).days
            else:
                rec.jours_restants = 0

    def action_renouveler(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renouveler le contrat'),
            'res_model': 'wizard.renouvellement',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contrat_id': self.id},
        }

    def action_export_contrats_expirants_excel(self):
        if not xlsxwriter:
            raise ValidationError(_("La bibliothèque xlsxwriter n'est pas installée."))

        today = fields.Date.today()
        date_60 = today + timedelta(days=60)
        contrats = self.search([
            ('date_fin', '>=', today),
            ('date_fin', '<=', date_60),
        ], order='date_fin')

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = workbook.add_worksheet('Contrats expirants')

        bold = workbook.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': 'white', 'border': 1})
        cell = workbook.add_format({'border': 1})
        money = workbook.add_format({'border': 1, 'num_format': '#,##0'})
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        red = workbook.add_format({'border': 1, 'bg_color': '#FFC7CE', 'bold': True})
        orange = workbook.add_format({'border': 1, 'bg_color': '#FFEB9C'})

        headers = ['Référence', 'Fournisseur', 'Type', 'Date début', 'Date fin', 'Jours restants', 'Montant (FCFA)', 'Équipements couverts', 'État']
        for col, h in enumerate(headers):
            ws.write(0, col, h, bold)
            ws.set_column(col, col, 22)

        for row, c in enumerate(contrats, start=1):
            jours = c.jours_restants
            fmt = red if jours <= 15 else orange
            ws.write(row, 0, c.name, fmt)
            ws.write(row, 1, c.fournisseur_id.name if c.fournisseur_id else '', fmt)
            ws.write(row, 2, dict(c._fields['type_contrat'].selection).get(c.type_contrat, ''), fmt)
            if c.date_debut:
                ws.write_datetime(row, 3, c.date_debut, date_fmt)
            else:
                ws.write(row, 3, '', fmt)
            if c.date_fin:
                ws.write_datetime(row, 4, c.date_fin, date_fmt)
            else:
                ws.write(row, 4, '', fmt)
            ws.write_number(row, 5, jours, fmt)
            ws.write_number(row, 6, c.montant or 0, money)
            equips = ', '.join(c.equipement_ids.mapped('name'))
            ws.write(row, 7, equips, cell)
            ws.write(row, 8, dict(c._fields['state'].selection).get(c.state, ''), cell)

        workbook.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'contrats_expirants_60j.xlsx',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
