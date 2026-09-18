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
    # Champs passifs de référence externe (préparation CLF-Expert) — vides pour l'instant.
    for _f in ("external_legal_object_id", "external_source_type", "external_version_id",
               "external_citation", "reference_date", "retrieved_at"):
        _t.setdefault(_f, None)

# Thème validé manuellement (niveau 2 activé) : A5 — Affichage public et publicité commerciale.
# Le texte de loi a été vérifié ; le moteur peut donc qualifier « non conforme » sur ce thème.
for _t in THEMES_LEGAUX:
    if _t["id"] == "A5":
        _t["texte_loi_valide"] = True
        _t["texte_loi"] = (
            "L'affichage public et la publicité commerciale doivent se faire en français. "
            "Ils peuvent également être faits à la fois en français et dans une autre langue "
            "pourvu que le français y figure de façon nettement prédominante "
            "(Charte de la langue française, art. 58)."
        )
        _t["external_source_type"] = "charte_langue_francaise"
        _t["external_citation"] = "Charte de la langue française, RLRQ c. C-11, art. 58"
        _t["reference_date"] = "2022-06-01"
        _t["retrieved_at"] = "2026-06-01"


# Thèmes validés manuellement — textes de loi confirmés (LégisQuébec, Loi 96).
# Niveau 2 activé : le moteur peut qualifier « non conforme » pour A1 à A4.
_A_TEXTES = {
    "A1": {
        "texte_loi": (
            "L'employeur doit respecter le droit du travailleur d'exercer ses activités en "
            "français; il est en conséquence notamment tenu : 1° de voir à ce que toute offre "
            "d'emploi, de mutation ou de promotion qu'il diffuse le soit en français; 2° de voir "
            "à ce que tout contrat individuel de travail qu'il conclut par écrit soit rédigé en "
            "français; 3° d'utiliser le français dans les communications écrites, même celles "
            "suivant la fin du lien d'emploi, qu'il adresse à son personnel, à une partie de "
            "celui-ci, à un travailleur en particulier ou à une association de travailleurs "
            "représentant son personnel ou une partie de celui-ci; 4° de voir à ce que les "
            "documents visés ci-dessous qu'il rend disponibles soient rédigés en français : "
            "a) les formulaires de demande d'emploi; b) les documents ayant trait aux conditions "
            "de travail; c) les documents de formation produits à l'intention de son personnel."
        ),
        "note_portee": (
            "Le paragraphe 4° énumère limitativement trois catégories de documents. L'article ne "
            "couvre ni les communications orales ni une catégorie générale d'« outils de travail » "
            "— ces éléments figurent dans le libellé du formulaire OQLF (libelle_oqlf), pas dans "
            "l'article lui-même. Ne jamais fusionner les deux dans le champ texte_loi."
        ),
        "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 41",
    },
    "A2": {
        "texte_loi": (
            "Art. 42 — Lorsqu'une offre visant à pourvoir un poste [...] est diffusée par un "
            "employeur dans une langue autre que le français en plus de l'offre qu'il est tenu de "
            "diffuser en français en vertu du paragraphe 1° du premier alinéa de l'article 41, il "
            "doit s'assurer que ces offres sont diffusées simultanément et par des moyens de "
            "transmission de même nature et atteignant un public cible de taille comparable."
        ),
        "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 41(1°) et 42",
    },
    "A3": {
        "texte_loi": (
            "Lorsque les personnes adhérant à un groupe couvert par un contrat d'assurance "
            "collective sont toutes des travailleurs [...], l'assureur est tenu de remettre au "
            "preneur une copie de la police rédigée en français; il en est de même des "
            "attestations d'assurance devant être distribuées à ces travailleurs."
        ),
        "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 50.1",
    },
    "A4": {
        "texte_loi": (
            "Art. 46 — Il est interdit à un employeur d'exiger d'une personne, pour qu'elle puisse "
            "rester en poste ou y accéder [...], la connaissance ou un niveau de connaissance "
            "spécifique d'une langue autre que la langue officielle, à moins que l'accomplissement "
            "de la tâche ne nécessite une telle connaissance; même alors, il doit, au préalable, "
            "avoir pris tous les moyens raisonnables pour éviter d'imposer une telle exigence. "
            "L'employeur qui exige cette connaissance pour accéder à un poste doit, lorsqu'il "
            "diffuse une offre visant à pourvoir ce poste, y indiquer les motifs justifiant cette "
            "exigence.\n"
            "Art. 46.1 — Un employeur est réputé ne pas avoir pris tous les moyens raisonnables "
            "[...] dès lors que, avant d'exiger cette connaissance [...], l'une des conditions "
            "suivantes n'est pas remplie : 1° il avait évalué les besoins linguistiques réels "
            "associés aux tâches à accomplir; 2° il s'était assuré que les connaissances "
            "linguistiques déjà exigées des autres membres du personnel étaient insuffisantes pour "
            "l'accomplissement de ces tâches; 3° il avait restreint le plus possible le nombre de "
            "postes auxquels se rattachent des tâches dont l'accomplissement nécessite cette "
            "connaissance. Le premier alinéa ne doit pas être interprété de façon à imposer à un "
            "employeur une réorganisation déraisonnable de son entreprise."
        ),
        "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 46 et 46.1",
    },
}
for _t in THEMES_LEGAUX:
    _spec = _A_TEXTES.get(_t["id"])
    if _spec:
        _t["texte_loi_valide"] = True
        _t["texte_loi"] = _spec["texte_loi"]
        if _spec.get("note_portee"):
            _t["note_portee"] = _spec["note_portee"]
        _t["external_source_type"] = "charte_langue_francaise"
        _t["external_citation"] = _spec["external_citation"]
        _t["reference_date"] = "2025-06-01"
        _t["retrieved_at"] = "2026-06-01"

# Thèmes B1 à B9 — article 141 (moyens du programme de francisation).
_ART141_CHAPEAU = ("141. Les programmes de francisation ont pour but la généralisation de "
                   "l'utilisation du français à tous les niveaux de l'entreprise, par :")
_B_PARAS = {
    "B1": "1° une bonne connaissance de la langue officielle chez les hauts dirigeants, les autres dirigeants, les membres des ordres professionnels et les autres membres du personnel;",
    "B2": "2° l'augmentation, s'il y a lieu, à tous les niveaux de l'entreprise, y compris au sein du conseil d'administration, du nombre de personnes ayant une bonne connaissance de la langue française de manière à en assurer l'utilisation généralisée;",
    "B3": "3° l'utilisation du français comme langue du travail et des communications internes;",
    "B4": "4° l'utilisation du français dans les documents et les outils de travail utilisés dans l'entreprise;",
    "B5": "5° l'utilisation du français dans les communications avec l'Administration, la clientèle, les fournisseurs, le public et les actionnaires sauf, dans ce dernier cas, s'il s'agit d'une société fermée au sens de la Loi sur les valeurs mobilières (chapitre V-1.1);",
    "B6": "6° l'utilisation d'une terminologie française;",
    "B7": "7° l'utilisation du français dans l'affichage public et la publicité commerciale;",
    "B8": "8° une politique d'embauche, de promotion et de mutation appropriée;",
    "B9": "9° l'utilisation du français dans les technologies de l'information.",
}
_ART141_NOTE = ("L'article 141 énonce que le BUT d'un programme de francisation est la généralisation "
                "de l'utilisation du français ; il énumère ensuite les MOYENS que l'employeur doit "
                "prendre pour l'atteindre. Il s'agit d'un objectif à pondérer, qui peut ne pas être "
                "entièrement atteint — les constats s'interprètent comme une obligation de moyens, "
                "non de résultat absolu.")
for _t in THEMES_LEGAUX:
    _para = _B_PARAS.get(_t["id"])
    if _para:
        _t["texte_loi_valide"] = True
        _t["texte_loi"] = _ART141_CHAPEAU + "\n" + _para
        _t["note_portee"] = _ART141_NOTE
        _t["external_source_type"] = "charte_langue_francaise"
        _t["external_citation"] = "Charte de la langue française, RLRQ c. C-11, art. 141"
        _t["reference_date"] = "2022-06-01"
        _t["retrieved_at"] = "2026-06-01"



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
