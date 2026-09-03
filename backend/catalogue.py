"""Catalogue fixe des thèmes légaux (Charte de la langue française / Loi 96).

Le champ `texte_loi` est un PLACEHOLDER dans cette itération : le texte exact des
articles de la Charte est validé manuellement, article par article, en dehors de ce
squelette. Ne pas générer de texte légal approximatif.
"""

# Niveau A — Obligations exécutoires universelles (chap. VI/VII de la Charte)
# Niveau B — Objectifs de généralisation (art. 141), certains font écho au Niveau A

THEMES_LEGAUX = [
    # ---- Niveau A ----
    {
        "id": "A1",
        "niveau": "A",
        "ordre": 1,
        "nom_theme": "Communications écrites de l'employeur",
        "theme_echo_id": None,
        "libelle_oqlf": "Communications écrites de l'employeur au personnel",
        "texte_loi": "",  # placeholder — texte validé dans une itération ultérieure
    },
    {
        "id": "A2",
        "niveau": "A",
        "ordre": 2,
        "nom_theme": "Offres d'emploi",
        "theme_echo_id": None,
        "libelle_oqlf": "Offres d'emploi, de mutation ou de promotion",
        "texte_loi": "",
    },
    {
        "id": "A3",
        "niveau": "A",
        "ordre": 3,
        "nom_theme": "Assurance collective",
        "theme_echo_id": None,
        "libelle_oqlf": "Contrats et documents d'assurance collective",
        "texte_loi": "",
    },
    {
        "id": "A4",
        "niveau": "A",
        "ordre": 4,
        "nom_theme": "Exigence de connaissance d'une autre langue",
        "theme_echo_id": None,
        "libelle_oqlf": "Exigence de la connaissance d'une autre langue que le français",
        "texte_loi": "",
    },
    {
        "id": "A5",
        "niveau": "A",
        "ordre": 5,
        "nom_theme": "Publicité commerciale, affichage, factures et documents commerciaux",
        "theme_echo_id": None,
        "libelle_oqlf": "Publicité commerciale, affichage public et documents commerciaux",
        "texte_loi": "",
    },
    # ---- Niveau B ----
    {
        "id": "B1",
        "niveau": "B",
        "ordre": 1,
        "nom_theme": "Connaissance du français (dirigeants, personnel)",
        "theme_echo_id": None,
        "libelle_oqlf": "Connaissance du français par les dirigeants et le personnel",
        "texte_loi": "",
    },
    {
        "id": "B2",
        "niveau": "B",
        "ordre": 2,
        "nom_theme": "Augmentation du nombre de personnes ayant une bonne connaissance du français",
        "theme_echo_id": None,
        "libelle_oqlf": "Augmentation du nombre de personnes connaissant bien le français",
        "texte_loi": "",
    },
    {
        "id": "B3",
        "niveau": "B",
        "ordre": 3,
        "nom_theme": "Langue du travail et des communications internes",
        "theme_echo_id": "A1",
        "libelle_oqlf": "Langue du travail et des communications internes",
        "texte_loi": "",
    },
    {
        "id": "B4",
        "niveau": "B",
        "ordre": 4,
        "nom_theme": "Documents et outils de travail",
        "theme_echo_id": "A1",
        "libelle_oqlf": "Documents et outils de travail en français",
        "texte_loi": "",
    },
    {
        "id": "B5",
        "niveau": "B",
        "ordre": 5,
        "nom_theme": "Communications externes (Administration, clientèle, fournisseurs, public, actionnaires)",
        "theme_echo_id": "A5",
        "libelle_oqlf": "Communications externes",
        "texte_loi": "",
    },
    {
        "id": "B6",
        "niveau": "B",
        "ordre": 6,
        "nom_theme": "Terminologie française",
        "theme_echo_id": None,
        "libelle_oqlf": "Utilisation d'une terminologie française",
        "texte_loi": "",
    },
    {
        "id": "B7",
        "niveau": "B",
        "ordre": 7,
        "nom_theme": "Affichage public et publicité commerciale",
        "theme_echo_id": "A5",
        "libelle_oqlf": "Affichage public et publicité commerciale",
        "texte_loi": "",
    },
    {
        "id": "B8",
        "niveau": "B",
        "ordre": 8,
        "nom_theme": "Politique d'embauche, de promotion et de mutation",
        "theme_echo_id": "A4",
        "libelle_oqlf": "Politique d'embauche, de promotion et de mutation",
        "texte_loi": "",
    },
    {
        "id": "B9",
        "niveau": "B",
        "ordre": 9,
        "nom_theme": "Technologies de l'information",
        "theme_echo_id": None,
        "libelle_oqlf": "Technologies de l'information",
        "texte_loi": "",
    },
]


# Chaque thème porte un drapeau de validation du texte légal (principe de prudence).
# Tant que texte_loi_valide == False, le moteur d'analyse reste au niveau « à valider ».
for _t in THEMES_LEGAUX:
    _t.setdefault("texte_loi_valide", False)


# Étapes du cycle de vie d'un dossier (pipeline légal)
PIPELINE_STAGES = [
    {"key": "inscription", "ordre": 1, "label": "Inscription de l'entreprise",
     "description": "Obligatoire dès 25 employés au Québec pendant 6 mois."},
    {"key": "analyse", "ordre": 2, "label": "Analyse de la situation linguistique",
     "description": "Module 1 — à transmettre dans les 3 mois suivant l'attestation d'inscription.", "module": 1},
    {"key": "comite", "ordre": 3, "label": "Constitution du comité de francisation",
     "description": "Requis si 100 employés ou plus."},
    {"key": "programme", "ordre": 4, "label": "Programme de francisation (PF)",
     "description": "Module 2 — catalogue de thèmes et mesures d'engagement.", "module": 2},
    {"key": "mise_en_oeuvre", "ordre": 5, "label": "Mise en œuvre (RMO)",
     "description": "Rapports de mise en œuvre — suivi des actions correctives (tous les 12 mois)."},
    {"key": "rapports_suivi", "ordre": 6, "label": "Rapports internes & preuves",
     "description": "Rapports périodiques et dossier de preuves de réalisation."},
    {"key": "certificat", "ordre": 7, "label": "Obtention du certificat de francisation",
     "description": "Délivrance du certificat de francisation par l'OQLF."},
    {"key": "maintien", "ordre": 8, "label": "Maintien (rapports triennaux)",
     "description": "Rapports triennaux post-certification."},
]
