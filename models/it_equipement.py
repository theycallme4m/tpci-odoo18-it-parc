import base64
import io
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class ItEquipement(models.Model):
    _name = 'it.equipement'
    _description = 'Équipement informatique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'reference desc'

    # --- Identification ---
    name = fields.Char(string='Nom', required=True, tracking=True)
    reference = fields.Char(
        string='Référence', readonly=True, default=lambda self: _('Nouveau'), copy=False
    )
    categorie_id = fields.Many2one('it.categorie', string='Catégorie', tracking=True, ondelete='restrict')
    serial_number = fields.Char(string='Numéro de série', tracking=True, copy=False)
    marque = fields.Char(string='Marque')
    modele = fields.Char(string='Modèle')
    image = fields.Image(string='Photo')

    # --- Financier / Garantie ---
    date_achat = fields.Date(string="Date d'achat", tracking=True)
    valeur_achat = fields.Float(string="Valeur d'achat (FCFA)", digits=(16, 0), tracking=True)
    date_garantie = fields.Date(string='Fin de garantie', tracking=True)
    jours_garantie = fields.Integer(compute='_compute_garantie', string='Jours restants (garantie)', store=False)
    garantie_expirante = fields.Boolean(compute='_compute_garantie', search='_search_garantie_expirante', string='Garantie expirante (30j)', store=False)

    # --- Localisation / Affectation ---
    localisation = fields.Char(string='Localisation', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employé affecté', tracking=True, ondelete='set null')
    department_id = fields.Many2one('hr.department', string='Département', tracking=True, ondelete='set null')

    # --- État ---
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('affecte', 'Affecté'),
        ('maintenance', 'En maintenance'),
        ('retire', 'Retiré'),
    ], string='État', default='brouillon', required=True, tracking=True)

    # --- Description ---
    description = fields.Text(string='Description technique')

    # --- Relations ---
    affectation_ids = fields.One2many('it.affectation', 'equipement_id', string='Historique des affectations')
    intervention_ids = fields.One2many('it.intervention', 'equipement_id', string='Interventions')
    contrat_ids = fields.Many2many(
        'it.contrat',
        'it_contrat_equipement_rel',
        'equipement_id', 'contrat_id',
        string='Contrats fournisseurs',
    )

    # --- Calculés ---
    nb_interventions = fields.Integer(compute='_compute_stats', string='Nb. interventions')
    cout_total_maintenance = fields.Float(compute='_compute_stats', string='Coût total maintenance (FCFA)', digits=(16, 0))

    # ------------------------------------------------------------------ #
    #  ORM overrides                                                       #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('it.equipement') or 'EQ-0000'
        return super().create(vals_list)

    # ------------------------------------------------------------------ #
    #  Constraints                                                         #
    # ------------------------------------------------------------------ #

    @api.constrains('serial_number')
    def _check_serial_unique(self):
        for rec in self:
            if rec.serial_number:
                domain = [('serial_number', '=', rec.serial_number), ('id', '!=', rec.id)]
                if self.search_count(domain):
                    raise ValidationError(
                        _("Le numéro de série '%s' est déjà enregistré.") % rec.serial_number
                    )

    # ------------------------------------------------------------------ #
    #  Computed fields                                                     #
    # ------------------------------------------------------------------ #

    @api.depends('date_garantie')
    def _compute_garantie(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_garantie:
                delta = (rec.date_garantie - today).days
                rec.jours_garantie = delta
                rec.garantie_expirante = 0 <= delta <= 30
            else:
                rec.jours_garantie = 0
                rec.garantie_expirante = False

    def _search_garantie_expirante(self, operator, value):
        today = fields.Date.today()
        date_limite = today + timedelta(days=30)
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('date_garantie', '>=', today), ('date_garantie', '<=', date_limite)]
        return ['|', ('date_garantie', '>', date_limite), ('date_garantie', '<', today)]

    @api.depends('intervention_ids', 'intervention_ids.cout')
    def _compute_stats(self):
        for rec in self:
            rec.nb_interventions = len(rec.intervention_ids)
            rec.cout_total_maintenance = sum(rec.intervention_ids.mapped('cout'))

    # ------------------------------------------------------------------ #
    #  Workflow actions                                                    #
    # ------------------------------------------------------------------ #

    def action_affecter(self):
        for rec in self:
            rec.write({'state': 'affecte'})

    def action_maintenance(self):
        for rec in self:
            rec.write({'state': 'maintenance'})

    def action_retirer(self):
        for rec in self:
            rec.write({'state': 'retire'})

    def action_brouillon(self):
        for rec in self:
            rec.write({'state': 'brouillon'})

    def action_reaffecter(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Réaffecter l\'équipement'),
            'res_model': 'wizard.reaffectation',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_equipement_id': self.id},
        }

    # ------------------------------------------------------------------ #
    #  Rapports PDF                                                        #
    # ------------------------------------------------------------------ #

    def action_print_fiche(self):
        return self.env.ref('it_parc.report_equipement_action').report_action(self)

    def action_print_inventaire(self):
        equipements = self.search([])
        return self.env.ref('it_parc.report_inventaire_action').report_action(equipements)

    def action_view_interventions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Interventions',
            'res_model': 'it.intervention',
            'view_mode': 'list,form',
            'domain': [('equipement_id', '=', self.id)],
            'context': {'default_equipement_id': self.id},
        }

    # ------------------------------------------------------------------ #
    #  Exports Excel                                                       #
    # ------------------------------------------------------------------ #

    def action_export_inventaire_excel(self):
        if not xlsxwriter:
            raise ValidationError(_("La bibliothèque xlsxwriter n'est pas installée (pip install xlsxwriter)."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = workbook.add_worksheet('Inventaire')

        # Formats
        bold = workbook.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': 'white', 'border': 1})
        cell = workbook.add_format({'border': 1})
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        money = workbook.add_format({'border': 1, 'num_format': '#,##0'})
        green = workbook.add_format({'border': 1, 'bg_color': '#C6EFCE'})
        orange = workbook.add_format({'border': 1, 'bg_color': '#FFEB9C'})
        red = workbook.add_format({'border': 1, 'bg_color': '#FFC7CE'})

        headers = [
            'Référence', 'Nom', 'Catégorie', 'Marque', 'Modèle',
            'N° Série', 'État', 'Employé', 'Département', 'Localisation',
            "Date d'achat", "Valeur d'achat (FCFA)", 'Fin de garantie',
            'Jours garantie', 'Nb. interventions', 'Coût maintenance (FCFA)',
        ]
        for col, h in enumerate(headers):
            ws.write(0, col, h, bold)
            ws.set_column(col, col, 18)

        states = {
            'brouillon': 'Brouillon',
            'affecte': 'Affecté',
            'maintenance': 'En maintenance',
            'retire': 'Retiré',
        }

        equipements = self.search([])
        for row, eq in enumerate(equipements, start=1):
            state_label = states.get(eq.state, eq.state)
            jours = eq.jours_garantie

            if jours < 0:
                g_fmt = red
            elif jours <= 30:
                g_fmt = orange
            else:
                g_fmt = green

            ws.write(row, 0, eq.reference or '', cell)
            ws.write(row, 1, eq.name, cell)
            ws.write(row, 2, eq.categorie_id.name if eq.categorie_id else '', cell)
            ws.write(row, 3, eq.marque or '', cell)
            ws.write(row, 4, eq.modele or '', cell)
            ws.write(row, 5, eq.serial_number or '', cell)
            ws.write(row, 6, state_label, cell)
            ws.write(row, 7, eq.employee_id.name if eq.employee_id else '', cell)
            ws.write(row, 8, eq.department_id.name if eq.department_id else '', cell)
            ws.write(row, 9, eq.localisation or '', cell)
            if eq.date_achat:
                ws.write_datetime(row, 10, eq.date_achat, date_fmt)
            else:
                ws.write(row, 10, '', cell)
            ws.write_number(row, 11, eq.valeur_achat or 0, money)
            if eq.date_garantie:
                ws.write_datetime(row, 12, eq.date_garantie, date_fmt)
            else:
                ws.write(row, 12, '', cell)
            ws.write(row, 13, jours, g_fmt)
            ws.write(row, 14, eq.nb_interventions, cell)
            ws.write_number(row, 15, eq.cout_total_maintenance or 0, money)

        workbook.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'inventaire_parc.xlsx',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_export_couts_maintenance_excel(self):
        if not xlsxwriter:
            raise ValidationError(_("La bibliothèque xlsxwriter n'est pas installée."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = workbook.add_worksheet('Coûts maintenance')

        bold = workbook.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': 'white', 'border': 1})
        cell = workbook.add_format({'border': 1})
        money = workbook.add_format({'border': 1, 'num_format': '#,##0'})
        date_fmt = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})

        headers = ['Équipement', 'Référence', 'Catégorie', 'Intervention', 'Type', 'Technicien', 'Date début', 'Durée (h)', 'Coût (FCFA)']
        for col, h in enumerate(headers):
            ws.write(0, col, h, bold)
            ws.set_column(col, col, 20)

        interventions = self.env['it.intervention'].search([], order='equipement_id, date_debut')
        for row, intv in enumerate(interventions, start=1):
            ws.write(row, 0, intv.equipement_id.name, cell)
            ws.write(row, 1, intv.equipement_id.reference or '', cell)
            ws.write(row, 2, intv.equipement_id.categorie_id.name if intv.equipement_id.categorie_id else '', cell)
            ws.write(row, 3, intv.name, cell)
            ws.write(row, 4, dict(intv._fields['type_intervention'].selection).get(intv.type_intervention, ''), cell)
            ws.write(row, 5, intv.technicien_id.name if intv.technicien_id else '', cell)
            if intv.date_debut:
                ws.write_datetime(row, 6, intv.date_debut.date(), date_fmt)
            else:
                ws.write(row, 6, '', cell)
            ws.write_number(row, 7, intv.duree or 0, cell)
            ws.write_number(row, 8, intv.cout or 0, money)

        workbook.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'couts_maintenance.xlsx',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    # ------------------------------------------------------------------ #
    #  Dashboard data                                                      #
    # ------------------------------------------------------------------ #

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.today()
        date_60 = today + timedelta(days=60)

        state_counts = {}
        for state in ['brouillon', 'affecte', 'maintenance', 'retire']:
            state_counts[state] = self.search_count([('state', '=', state)])

        total = sum(state_counts.values())
        contrats_expirant = self.env['it.contrat'].search_count([
            ('date_fin', '<=', date_60),
            ('date_fin', '>=', today),
            ('state', '=', 'actif'),
        ])
        garanties_expirantes = self.search_count([
            ('date_garantie', '<=', date_60),
            ('date_garantie', '>=', today),
            ('state', '!=', 'retire'),
        ])
        total_cout = sum(self.env['it.intervention'].search([]).mapped('cout'))

        max_count = max(state_counts.values()) if any(state_counts.values()) else 1
        colors = {
            'brouillon': '#6c757d',
            'affecte': '#28a745',
            'maintenance': '#ffc107',
            'retire': '#dc3545',
        }
        labels = {
            'brouillon': 'Brouillon',
            'affecte': 'Affecté',
            'maintenance': 'Maintenance',
            'retire': 'Retiré',
        }
        chart_data = [
            {
                'label': labels[s],
                'count': state_counts[s],
                'color': colors[s],
                'height': int(state_counts[s] / max_count * 180) if max_count else 0,
            }
            for s in ['brouillon', 'affecte', 'maintenance', 'retire']
        ]

        return {
            'total_equipements': total,
            'equipements_affectes': state_counts['affecte'],
            'equipements_maintenance': state_counts['maintenance'],
            'contrats_expirant': contrats_expirant,
            'garanties_expirantes': garanties_expirantes,
            'total_cout_maintenance': total_cout,
            'chart_data': chart_data,
        }
