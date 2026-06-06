from odoo import _, api, fields, models


class WizardScanAlertes(models.TransientModel):
    _name = 'wizard.scan.alertes'
    _description = 'Assistant de scan des alertes'

    delai_jours = fields.Integer(
        string='Délai (jours)',
        required=True,
        default=30,
        help="Générer des alertes pour les garanties et contrats expirant dans ce nombre de jours.",
    )
    nb_alertes_creees = fields.Integer(string='Alertes créées', readonly=True)
    rapport = fields.Text(string='Résultat', readonly=True)
    state = fields.Selection([
        ('input', 'Paramétrage'),
        ('done', 'Résultat'),
    ], default='input')

    def action_scanner(self):
        self.ensure_one()
        avant = self.env['it.alerte'].search_count([('state', '=', 'active')])
        self.env['it.alerte']._generer_alertes(self.delai_jours)
        apres = self.env['it.alerte'].search_count([('state', '=', 'active')])
        nb = apres - avant

        self.write({
            'nb_alertes_creees': nb,
            'rapport': _("%d nouvelle(s) alerte(s) générée(s) pour un délai de %d jours.") % (nb, self.delai_jours),
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_voir_alertes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Alertes actives'),
            'res_model': 'it.alerte',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'active')],
        }
