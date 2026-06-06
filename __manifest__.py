{
    'name': 'IT Parc - Gestion de parc informatique',
    'version': '18.0.1.0.0',
    'category': 'IT Management',
    'summary': 'Gestion du parc informatique de TECHPARK CI',
    'description': """
        Module de gestion du parc informatique pour TECHPARK CI.
        Équipements, affectations, interventions, contrats, alertes,
        rapports PDF, exports Excel et tableau de bord OWL.
    """,
    'author': 'TECHPARK CI',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'web',
        'purchase',
        'account',
    ],
    'data': [
        'security/it_parc_security.xml',
        'security/ir.model.access.csv',
        'data/it_parc_data.xml',
        'views/it_categorie_views.xml',
        'views/it_equipement_views.xml',
        'views/it_affectation_views.xml',
        'views/it_intervention_views.xml',
        'views/it_contrat_views.xml',
        'views/it_alerte_views.xml',
        'views/wizard_reaffectation_views.xml',
        'views/wizard_renouvellement_views.xml',
        'views/wizard_scan_alertes_views.xml',
        'views/wizard_import_csv_views.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        'report/report_actions.xml',
        'report/report_equipement_template.xml',
        'report/report_inventaire_template.xml',
        'report/report_interventions_template.xml',
    ],
    'demo': [
        'data/it_parc_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'it_parc/static/src/css/it_parc_dashboard.css',
            'it_parc/static/src/xml/it_parc_dashboard.xml',
            'it_parc/static/src/js/it_parc_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
}
