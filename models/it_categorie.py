from odoo import fields, models


class ItCategorie(models.Model):
    _name = 'it.categorie'
    _description = 'Catégorie d\'équipement'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Couleur')
    equipement_ids = fields.One2many('it.equipement', 'categorie_id', string='Équipements')
    nb_equipements = fields.Integer(compute='_compute_nb_equipements', string='Nb. équipements')

    def _compute_nb_equipements(self):
        for rec in self:
            rec.nb_equipements = len(rec.equipement_ids)
