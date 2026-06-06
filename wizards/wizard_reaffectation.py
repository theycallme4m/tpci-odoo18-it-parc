from odoo import _, api, fields, models


class WizardReaffectation(models.TransientModel):
    _name = 'wizard.reaffectation'
    _description = 'Assistant de réaffectation d\'équipement'

    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True, readonly=True)
    ancien_employee_id = fields.Many2one(related='equipement_id.employee_id', string='Employé actuel', readonly=True)
    ancien_department_id = fields.Many2one(related='equipement_id.department_id', string='Département actuel', readonly=True)

    employee_id = fields.Many2one('hr.employee', string='Nouvel employé', required=True)
    department_id = fields.Many2one('hr.department', string='Nouveau département')
    date_debut = fields.Date(string='Date effective', required=True, default=fields.Date.today)
    motif = fields.Text(string='Motif de la réaffectation', required=True)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    def action_confirmer(self):
        self.ensure_one()
        eq = self.equipement_id

        # Clôturer l'affectation courante
        current = self.env['it.affectation'].search([
            ('equipement_id', '=', eq.id),
            ('date_fin', '=', False),
        ])
        current.write({'date_fin': self.date_debut})

        # Créer la nouvelle affectation
        self.env['it.affectation'].create({
            'equipement_id': eq.id,
            'employee_id': self.employee_id.id,
            'department_id': self.department_id.id if self.department_id else False,
            'date_debut': self.date_debut,
            'motif': self.motif,
        })

        # Mettre à jour l'équipement
        eq.write({
            'employee_id': self.employee_id.id,
            'department_id': self.department_id.id if self.department_id else False,
            'state': 'affecte',
        })

        eq.message_post(
            body=_("Réaffectation : %s → %s (%s). Motif : %s") % (
                self.ancien_employee_id.name if self.ancien_employee_id else '-',
                self.employee_id.name,
                self.date_debut,
                self.motif,
            )
        )

        return {'type': 'ir.actions.act_window_close'}
