from odoo import _, api, fields, models


class ItIntervention(models.Model):
    _name = 'it.intervention'
    _description = 'Intervention de maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_debut desc'

    name = fields.Char(string='Titre', required=True, tracking=True)
    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True, tracking=True, ondelete='cascade')
    type_intervention = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Préventive'),
    ], string='Type', required=True, default='corrective', tracking=True)

    technicien_id = fields.Many2one('hr.employee', string='Technicien', tracking=True, ondelete='set null')
    date_debut = fields.Datetime(string='Date de début', tracking=True)
    date_fin = fields.Datetime(string='Date de fin', tracking=True)
    duree = fields.Float(compute='_compute_duree', string='Durée (heures)', store=True)
    cout = fields.Float(string='Coût (FCFA)', digits=(16, 0), tracking=True)

    description = fields.Text(string='Description du problème')
    rapport = fields.Text(string="Rapport d'intervention")

    state = fields.Selection([
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
    ], string='État', default='planifie', tracking=True)

    @api.depends('date_debut', 'date_fin')
    def _compute_duree(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_fin > rec.date_debut:
                delta = rec.date_fin - rec.date_debut
                rec.duree = delta.total_seconds() / 3600.0
            else:
                rec.duree = 0.0

    def action_demarrer(self):
        self.write({'state': 'en_cours'})

    def action_terminer(self):
        self.write({'state': 'termine'})

    def action_planifier(self):
        self.write({'state': 'planifie'})

    def action_print_rapport(self):
        return self.env.ref('it_parc.report_interventions_action').report_action(self)
