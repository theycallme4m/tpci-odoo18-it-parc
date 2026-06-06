from odoo import api, fields, models


class ItAffectation(models.Model):
    _name = 'it.affectation'
    _description = 'Historique d\'affectation'
    _order = 'date_debut desc'
    _rec_name = 'equipement_id'

    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employé', required=True, ondelete='restrict')
    department_id = fields.Many2one('hr.department', string='Département', ondelete='set null')
    date_debut = fields.Date(string='Date de début', required=True, default=fields.Date.today)
    date_fin = fields.Date(string='Date de fin')
    motif = fields.Text(string='Motif de la mutation')
    user_id = fields.Many2one('res.users', string='Enregistré par', default=lambda self: self.env.user)
    active = fields.Boolean(default=True)

