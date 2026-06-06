import base64
import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WizardImportCsv(models.TransientModel):
    _name = 'wizard.import.csv'
    _description = 'Assistant d\'import CSV d\'équipements'

    fichier_csv = fields.Binary(string='Fichier CSV', required=True, attachment=False)
    nom_fichier = fields.Char(string='Nom du fichier')
    separateur = fields.Selection([
        (',', 'Virgule (,)'),
        (';', 'Point-virgule (;)'),
        ('\t', 'Tabulation'),
    ], string='Séparateur', default=';', required=True)

    # Résultats
    state = fields.Selection([('input', 'Import'), ('done', 'Résultat')], default='input')
    nb_crees = fields.Integer(string='Créés', readonly=True)
    nb_ignores = fields.Integer(string='Ignorés (doublons)', readonly=True)
    nb_erreurs = fields.Integer(string='Erreurs', readonly=True)
    rapport = fields.Text(string='Rapport d\'import', readonly=True)

    def action_importer(self):
        self.ensure_one()
        if not self.fichier_csv:
            raise UserError(_("Veuillez sélectionner un fichier CSV."))

        contenu = base64.b64decode(self.fichier_csv).decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(contenu), delimiter=self.separateur)

        # Colonnes attendues (min.)
        champs_requis = {'name'}
        lignes_creees = []
        lignes_ignorees = []
        lignes_erreur = []

        for i, row in enumerate(reader, start=2):
            row = {k.strip(): (v or '').strip() for k, v in row.items() if k}
            if not champs_requis.issubset(set(row.keys())):
                lignes_erreur.append(_("Ligne %d : colonne 'name' manquante.") % i)
                continue

            name = row.get('name', '').strip()
            serial = row.get('serial_number', '').strip()

            if not name:
                lignes_erreur.append(_("Ligne %d : nom vide.") % i)
                continue

            # Doublon par numéro de série
            if serial:
                existing = self.env['it.equipement'].search([('serial_number', '=', serial)], limit=1)
                if existing:
                    lignes_ignorees.append(_("Ligne %d : n° série '%s' déjà existant (%s).") % (i, serial, existing.name))
                    continue

            # Résolution de la catégorie
            categorie_id = False
            if row.get('categorie'):
                cat = self.env['it.categorie'].search([('name', 'ilike', row['categorie'])], limit=1)
                if not cat:
                    cat = self.env['it.categorie'].create({'name': row['categorie']})
                categorie_id = cat.id

            vals = {
                'name': name,
                'serial_number': serial or False,
                'categorie_id': categorie_id,
                'marque': row.get('marque') or False,
                'modele': row.get('modele') or False,
                'localisation': row.get('localisation') or False,
                'description': row.get('description') or False,
            }

            # Champs date
            for date_field, col in [('date_achat', 'date_achat'), ('date_garantie', 'date_garantie')]:
                val = row.get(col, '').strip()
                if val:
                    try:
                        from datetime import datetime
                        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
                            try:
                                vals[date_field] = datetime.strptime(val, fmt).date()
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

            # Valeur d'achat
            va = row.get('valeur_achat', '').replace(' ', '').replace(',', '.').replace('\xa0', '')
            if va:
                try:
                    vals['valeur_achat'] = float(va)
                except ValueError:
                    pass

            try:
                eq = self.env['it.equipement'].create(vals)
                lignes_creees.append(_("Ligne %d : '%s' créé (réf. %s).") % (i, name, eq.reference))
            except Exception as e:
                lignes_erreur.append(_("Ligne %d : erreur création '%s' - %s") % (i, name, str(e)))

        rapport_lines = []
        if lignes_creees:
            rapport_lines.append("=== CRÉÉS (%d) ===" % len(lignes_creees))
            rapport_lines.extend(lignes_creees)
        if lignes_ignorees:
            rapport_lines.append("\n=== IGNORÉS - DOUBLONS (%d) ===" % len(lignes_ignorees))
            rapport_lines.extend(lignes_ignorees)
        if lignes_erreur:
            rapport_lines.append("\n=== ERREURS (%d) ===" % len(lignes_erreur))
            rapport_lines.extend(lignes_erreur)

        self.write({
            'nb_crees': len(lignes_creees),
            'nb_ignores': len(lignes_ignorees),
            'nb_erreurs': len(lignes_erreur),
            'rapport': '\n'.join(rapport_lines) if rapport_lines else _("Aucune ligne traitée."),
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
