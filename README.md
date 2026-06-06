# IT Parc — Module Odoo 18 de gestion de parc informatique

Module développé pour **TECHPARK CI** (Abidjan, Côte d'Ivoire).  
Version : **18.0.1.0.0** | Licence : LGPL-3

---

## Fonctionnalités

| N° | Fonctionnalité | Description |
|----|----------------|-------------|
| 01 | Gestion des équipements | Enregistrement avec workflow 4 états : Brouillon → Affecté → En maintenance → Retiré |
| 02 | Affectation employés | Liaison équipement/employé/département avec historique et wizard de réaffectation |
| 03 | Suivi des interventions | Maintenance corrective/préventive avec durée calculée, coût et vue calendrier |
| 04 | Contrats fournisseurs | Suivi de validité, jours restants, wizard de renouvellement |
| 05 | Alertes automatiques | Génération d'alertes garanties/contrats par cron ou scan manuel |
| 06 | Import CSV | Wizard d'import en masse avec détection des doublons par numéro de série |
| 07 | Rapports PDF (QWeb) | Fiche équipement, inventaire complet, rapport d'intervention |
| 08 | Exports Excel | Inventaire, coûts maintenance, contrats expirant dans 60 jours |
| 09 | Dashboard OWL | 6 KPIs + graphique SVG des équipements par état |

---

## Prérequis

- **Odoo 18 Enterprise** (Community compatible avec ajustements mineurs)
- **Python 3.11+**
- Modules Odoo installés : `base`, `hr`, `mail`, `web`, `purchase`, `account`
- Bibliothèque Python xlsxwriter :
  ```bash
  pip install xlsxwriter
  ```

---

## Installation

### 1. Copier le module

Placer le dossier `it_parc/` dans votre répertoire d'addons Odoo :

```
/path/to/odoo/addons/it_parc/
```

Ou ajouter le chemin dans `odoo.conf` :

```ini
addons_path = /path/to/odoo/addons,/chemin/vers/it_parc_parent
```

### 2. Installer xlsxwriter

```bash
pip install xlsxwriter
```

### 3. Mettre à jour la liste des modules

Dans Odoo → Paramètres → Activer le mode développeur → Mise à jour de la liste des applications.

Ou en ligne de commande :

```bash
python odoo-bin -c odoo.conf --update=it_parc --stop-after-init
```

### 4. Installer le module

Interface Odoo : Applications → rechercher **IT Parc** → Installer.

Ou en ligne de commande :

```bash
python odoo-bin -c odoo.conf -i it_parc --stop-after-init
```

### 5. Charger les données de démo (optionnel)

Les données de démo se chargent automatiquement si l'option **Données de démonstration** est activée lors de l'installation de la base de données. Le fichier `data/it_parc_demo.xml` fournit :

- 5 catégories d'équipements
- 3 départements et 5 employés
- 3 fournisseurs
- **11 équipements** (postes, serveurs, réseau, imprimantes, téléphones)
- **3 contrats** fournisseurs
- **5 interventions** (correctives et préventives)

---

## Groupes de sécurité

| Groupe | Droits |
|--------|--------|
| **IT Technicien** | Lecture sur équipements, création/modification d'interventions |
| **IT Manager** | Accès complet (CRUD sur tous les modèles, rapports, exports) |

Pour attribuer un groupe : Paramètres → Utilisateurs & Sociétés → Utilisateurs → choisir l'utilisateur → section **IT Parc**.

---

## Structure du module

```
it_parc/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py                    # Contrôleur JSON-RPC dashboard
├── data/
│   ├── it_parc_data.xml           # Séquence + cron + paramètres
│   └── it_parc_demo.xml           # Données de démonstration
├── models/
│   ├── __init__.py
│   ├── it_categorie.py            # Catégories d'équipements
│   ├── it_equipement.py           # Modèle central (+ exports Excel + dashboard)
│   ├── it_affectation.py          # Historique affectations
│   ├── it_intervention.py         # Interventions maintenance
│   ├── it_contrat.py              # Contrats fournisseurs (+ export Excel)
│   └── it_alerte.py               # Alertes + cron
├── report/
│   ├── report_actions.xml         # Déclarations ir.actions.report
│   ├── report_equipement_template.xml
│   ├── report_inventaire_template.xml
│   └── report_interventions_template.xml
├── security/
│   ├── ir.model.access.csv
│   └── it_parc_security.xml       # Groupes + règles d'accès
├── static/
│   └── src/
│       ├── css/it_parc_dashboard.css
│       ├── js/it_parc_dashboard.js    # Composant OWL
│       └── xml/it_parc_dashboard.xml  # Template OWL
├── views/
│   ├── it_categorie_views.xml
│   ├── it_equipement_views.xml    # Liste, Kanban, Form, recherche
│   ├── it_affectation_views.xml
│   ├── it_intervention_views.xml  # + Vue calendrier
│   ├── it_contrat_views.xml
│   ├── it_alerte_views.xml
│   ├── wizard_reaffectation_views.xml
│   ├── wizard_renouvellement_views.xml
│   ├── wizard_scan_alertes_views.xml
│   ├── wizard_import_csv_views.xml
│   ├── dashboard_views.xml        # Action client OWL
│   └── menu_views.xml
└── wizards/
    ├── __init__.py
    ├── wizard_reaffectation.py
    ├── wizard_renouvellement.py
    ├── wizard_scan_alertes.py
    └── wizard_import_csv.py
```

---

## Utilisation

### Format CSV pour l'import en masse

```csv
name;serial_number;categorie;marque;modele;localisation;date_achat;valeur_achat;date_garantie;description
Dell OptiPlex 7090;DELL-7090-ABC;Poste de travail;Dell;OptiPlex 7090;Bureau 101;15/03/2023;650000;15/03/2026;PC bureautique standard
```

- Séparateur configurable (`;`, `,` ou tabulation)
- Dates acceptées : `DD/MM/YYYY` ou `YYYY-MM-DD`
- Doublons détectés par **numéro de série**
- Les catégories inexistantes sont créées automatiquement

### Alertes automatiques

La tâche planifiée `it_parc_cron` s'exécute quotidiennement et génère des alertes pour :
- Les **garanties** expirant dans les 30 prochains jours (paramétrable)
- Les **contrats** expirant dans les 30 prochains jours

Délai configurable : Paramètres → Paramètres système → clé `it_parc.delai_alerte`.

Scan manuel disponible via : IT Parc → Alertes → Générer les alertes.

---

## Dashboard OWL

Le tableau de bord se trouve dans le menu **IT Parc → Tableau de bord**.

KPIs affichés :
1. Total des équipements
2. Équipements affectés
3. Équipements en maintenance
4. Garanties expirantes (30 jours)
5. Contrats expirant (60 jours)
6. Coût total de maintenance (FCFA)

Graphique : répartition des équipements par état (SVG natif, aucun framework tiers).

---

## Auteur

Module développé pour **TECHPARK CI** — Abidjan, Côte d'Ivoire — Juin 2026.
