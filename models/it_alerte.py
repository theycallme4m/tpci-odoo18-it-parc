from datetime import timedelta

from odoo import _, api, fields, models


class ItAlerte(models.Model):
    _name = 'it.alerte'
    _description = 'Alerte de garantie ou de contrat'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'date_expiration'

    name = fields.Char(string='Alerte', required=True)
    type_alerte = fields.Selection([
        ('garantie', 'Garantie équipement'),
        ('contrat', 'Contrat fournisseur'),
    ], string='Type', required=True, tracking=True)

    equipement_id = fields.Many2one('it.equipement', string='Équipement', ondelete='cascade')
    contrat_id = fields.Many2one('it.contrat', string='Contrat', ondelete='cascade')

    date_expiration = fields.Date(string='Date d\'expiration', required=True)
    jours_restants = fields.Integer(compute='_compute_jours', search='_search_jours_restants', string='Jours restants', store=False)
    message = fields.Text(string='Message')

    state = fields.Selection([
        ('active', 'Active'),
        ('traitee', 'Traitée'),
    ], string='État', default='active', tracking=True)

    def _search_jours_restants(self, operator, value):
        today = fields.Date.today()
        if operator == '<=':
            return [('date_expiration', '>=', today), ('date_expiration', '<=', today + timedelta(days=value))]
        if operator == '<':
            return [('date_expiration', '>=', today), ('date_expiration', '<=', today + timedelta(days=value - 1))]
        if operator == '>=':
            return [('date_expiration', '>=', today + timedelta(days=value))]
        if operator == '>':
            return [('date_expiration', '>=', today + timedelta(days=value + 1))]
        if operator == '=':
            return [('date_expiration', '=', today + timedelta(days=value))]
        return []

    @api.depends('date_expiration')
    def _compute_jours(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_expiration:
                rec.jours_restants = (rec.date_expiration - today).days
            else:
                rec.jours_restants = 0

    def action_traiter(self):
        self.write({'state': 'traitee'})

    def action_reactivate(self):
        self.write({'state': 'active'})

    @api.model
    def _cron_generer_alertes(self):
        """Tâche planifiée : génère les alertes pour garanties et contrats expirant bientôt."""
        delai = int(self.env['ir.config_parameter'].sudo().get_param('it_parc.delai_alerte', default=30))
        self._generer_alertes(delai)

    @api.model
    def _generer_alertes(self, delai=30):
        today = fields.Date.today()
        date_limite = today + timedelta(days=delai)

        # Alertes garantie
        equipements = self.env['it.equipement'].search([
            ('date_garantie', '>=', today),
            ('date_garantie', '<=', date_limite),
            ('state', '!=', 'retire'),
        ])
        for eq in equipements:
            existing = self.search([
                ('type_alerte', '=', 'garantie'),
                ('equipement_id', '=', eq.id),
                ('state', '=', 'active'),
            ])
            if not existing:
                self.create({
                    'name': _('Garantie expirante : %s') % eq.name,
                    'type_alerte': 'garantie',
                    'equipement_id': eq.id,
                    'date_expiration': eq.date_garantie,
                    'message': _('La garantie de l\'équipement "%s" (réf. %s) expire le %s.') % (
                        eq.name, eq.reference, eq.date_garantie
                    ),
                })

        # Alertes contrat
        contrats = self.env['it.contrat'].search([
            ('date_fin', '>=', today),
            ('date_fin', '<=', date_limite),
            ('state', '=', 'actif'),
        ])
        for ct in contrats:
            existing = self.search([
                ('type_alerte', '=', 'contrat'),
                ('contrat_id', '=', ct.id),
                ('state', '=', 'active'),
            ])
            if not existing:
                self.create({
                    'name': _('Contrat expirant : %s') % ct.name,
                    'type_alerte': 'contrat',
                    'contrat_id': ct.id,
                    'date_expiration': ct.date_fin,
                    'message': _('Le contrat "%s" avec %s expire le %s.') % (
                        ct.name,
                        ct.fournisseur_id.name if ct.fournisseur_id else '',
                        ct.date_fin,
                    ),
                })
