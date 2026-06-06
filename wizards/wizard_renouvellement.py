from odoo import _, api, fields, models


class WizardRenouvellement(models.TransientModel):
    _name = 'wizard.renouvellement'
    _description = 'Assistant de renouvellement de contrat'

    contrat_id = fields.Many2one('it.contrat', string='Contrat à renouveler', required=True, readonly=True)
    ancien_date_fin = fields.Date(related='contrat_id.date_fin', string='Ancienne date de fin', readonly=True)

    nouvelle_date_debut = fields.Date(string='Nouvelle date de début', required=True, default=fields.Date.today)
    nouvelle_date_fin = fields.Date(string='Nouvelle date de fin', required=True)
    nouveau_montant = fields.Float(string='Nouveau montant (FCFA)', digits=(16, 0))
    notes = fields.Text(string='Notes de renouvellement')

    @api.onchange('contrat_id')
    def _onchange_contrat(self):
        if self.contrat_id:
            self.nouveau_montant = self.contrat_id.montant

    def action_confirmer(self):
        self.ensure_one()
        ct = self.contrat_id

        # Marquer l'ancien comme renouvelé
        ct.write({'state': 'renouvele'})

        # Créer le nouveau contrat
        nouveau = ct.copy({
            'name': ct.name + ' (Renouvelé)',
            'date_debut': self.nouvelle_date_debut,
            'date_fin': self.nouvelle_date_fin,
            'montant': self.nouveau_montant,
            'state': 'actif',
            'description': self.notes or ct.description,
        })

        ct.message_post(
            body=_("Contrat renouvelé. Nouveau contrat créé : %s (du %s au %s).") % (
                nouveau.name, self.nouvelle_date_debut, self.nouvelle_date_fin
            )
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouveau contrat'),
            'res_model': 'it.contrat',
            'view_mode': 'form',
            'res_id': nouveau.id,
        }
