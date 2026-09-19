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



# ==================================================================
# Régime A — Obligations UNIVERSELLES (chap. VI/VII de la Charte),
# applicables à TOUTE entreprise peu importe la taille (dont < 25 employés).
# Textes vérifiés sur LégisQuébec : texte_loi_valide = True dès la création.
# U1/U2/U6/U8/U15 sont PARTAGÉS avec A1/A2/A4/A3/A5 (même source légale) :
# aucune duplication du texte — on réutilise l'entrée du catalogue existant.
# ==================================================================
_A_BY_ID = {t["id"]: t for t in THEMES_LEGAUX}


def _shared_theme(u_id, a_id, ordre, nom, article):
    a = _A_BY_ID[a_id]
    return {
        "id": u_id, "niveau": "U", "ordre": ordre, "regime": "A",
        "shared_ref": a_id, "nom_theme": nom, "article": article,
        "theme_echo_id": None, "libelle_oqlf": a.get("libelle_oqlf", nom),
        "texte_loi": a.get("texte_loi", ""),
        "texte_loi_valide": a.get("texte_loi_valide", True),
        "note_portee": a.get("note_portee"),
        "external_legal_object_id": None, "external_version_id": None,
        "external_source_type": "charte_langue_francaise",
        "external_citation": a.get("external_citation"),
        "reference_date": a.get("reference_date"), "retrieved_at": a.get("retrieved_at"),
        "prioritaire_amorce": True,
    }


def _uni_theme(u_id, ordre, nom, article, texte, citation, prioritaire=True, valide=True):
    return {
        "id": u_id, "niveau": "U", "ordre": ordre, "regime": "A",
        "shared_ref": None, "nom_theme": nom, "article": article,
        "theme_echo_id": None, "libelle_oqlf": nom,
        "texte_loi": texte, "texte_loi_valide": valide, "note_portee": None,
        "external_legal_object_id": None, "external_version_id": None,
        "external_source_type": "charte_langue_francaise", "external_citation": citation,
        "reference_date": "2022-06-01", "retrieved_at": "2026-06-01",
        "prioritaire_amorce": prioritaire,
    }


UNIVERSAL_THEMES = [
    _shared_theme("U1", "A1", 1, "Communications écrites de l'employeur", "art. 41"),
    _shared_theme("U2", "A2", 2, "Offres d'emploi diffusées simultanément", "art. 42"),
    _uni_theme("U3", 3, "Conventions et ententes collectives rédigées en français", "art. 43-44",
        ("Art. 43 : Les conventions collectives et leurs annexes doivent être rédigées dans la langue "
         "officielle [...]. Une entente collective, si elle n'est pas déjà rédigée en français, doit "
         "également être disponible dans cette langue dès sa conclusion.\n"
         "Art. 44 : Une version française doit être jointe immédiatement et sans délai à toute sentence "
         "arbitrale rendue en anglais à la suite de l'arbitrage d'un grief, d'une mésentente ou d'un "
         "différend [...]."),
        "Charte de la langue française, RLRQ c. C-11, art. 43 et 44"),
    _uni_theme("U4", 4, "Interdiction de représailles liées à la langue", "art. 45",
        ("Il est interdit à un employeur de congédier, de mettre à pied, de rétrograder ou de déplacer "
         "un membre de son personnel, d'exercer à son endroit des représailles ou de lui imposer toute "
         "autre sanction pour la seule raison que ce dernier ne parle que le français ou qu'il ne "
         "connaît pas suffisamment une langue donnée autre que la langue officielle, ou pour l'un ou "
         "l'autre des motifs [liés à l'exercice de ses droits linguistiques] énumérés à l'article."),
        "Charte de la langue française, RLRQ c. C-11, art. 45"),
    _uni_theme("U5", 5, "Milieu de travail exempt de discrimination linguistique", "art. 45.1",
        ("Tout salarié a droit à un milieu de travail qui soit exempt de discrimination ou de "
         "harcèlement parce qu'il ne maîtrise pas ou peu une langue autre que la langue officielle, "
         "parce qu'il revendique la possibilité de s'exprimer dans la langue officielle ou parce qu'il "
         "a exigé le respect d'un droit découlant des dispositions du présent chapitre. L'employeur "
         "doit prendre les moyens raisonnables pour prévenir ce type de conduite et, lorsqu'elle est "
         "portée à sa connaissance, pour la faire cesser."),
        "Charte de la langue française, RLRQ c. C-11, art. 45.1"),
    _shared_theme("U6", "A4", 6, "Exigence de connaissance d'une autre langue", "art. 46, 46.1"),
    _uni_theme("U7", 7, "Communications de l'association de travailleurs", "art. 48-49",
        ("Art. 49 : Une association de travailleurs utilise la langue officielle dans les "
         "communications écrites et orales avec ses membres. Il lui est loisible d'utiliser la langue "
         "de son interlocuteur lorsqu'elle communique avec un membre qui lui en a fait la demande."),
        "Charte de la langue française, RLRQ c. C-11, art. 48 et 49"),
    _shared_theme("U8", "A3", 8, "Assurance collective", "art. 50.1"),
    _uni_theme("U9", 9, "Droit d'être informé et servi en français", "art. 50.2",
        ("L'entreprise qui offre au consommateur des biens ou des services doit respecter son droit "
         "d'être informé et servi en français. L'entreprise qui offre à un public autre que des "
         "consommateurs des biens et des services doit l'informer et le servir en français."),
        "Charte de la langue française, RLRQ c. C-11, art. 50.2"),
    _uni_theme("U10", 10, "Inscriptions sur produits, emballages, menus", "art. 51, 51.1",
        ("Toute inscription sur un produit, sur son contenant ou sur son emballage, sur un document ou "
         "objet accompagnant ce produit, y compris le mode d'emploi et les certificats de garantie, "
         "doit être rédigée en français. Cette règle s'applique également aux menus et aux cartes des "
         "vins. Le texte français peut être assorti d'une ou plusieurs traductions, mais aucune "
         "inscription rédigée dans une autre langue ne doit l'emporter sur celle qui est rédigée en "
         "français ni être accessible dans des conditions plus favorables."),
        "Charte de la langue française, RLRQ c. C-11, art. 51 et 51.1"),
    _uni_theme("U11", 11, "Catalogues, brochures, documents commerciaux", "art. 52",
        ("Quel qu'en soit le support, les catalogues, les brochures, les dépliants, les annuaires "
         "commerciaux, les bons de commande et tout autre document de même nature qui sont disponibles "
         "au public doivent être rédigés en français."),
        "Charte de la langue française, RLRQ c. C-11, art. 52"),
    _uni_theme("U12", 12, "Logiciels disponibles en français", "art. 52.1",
        ("Tout logiciel, y compris tout ludiciel ou système d'exploitation, qu'il soit installé ou "
         "non, doit être disponible en français, à moins qu'il n'en existe aucune version française."),
        "Charte de la langue française, RLRQ c. C-11, art. 52.1"),
    _uni_theme("U13", 13, "Contrats d'adhésion", "art. 55",
        ("Les contrats d'adhésion ainsi que les documents qui s'y rattachent sont rédigés en français. "
         "Les parties peuvent être liées seulement par sa version dans une autre langue que le français "
         "si, après que sa version française a été remise à l'adhérent, telle est leur volonté expresse."),
        "Charte de la langue française, RLRQ c. C-11, art. 55"),
    _uni_theme("U14", 14, "Factures, reçus, quittances", "art. 57",
        ("Les factures, les reçus, les quittances et les autres documents de même nature sont rédigés "
         "en français."),
        "Charte de la langue française, RLRQ c. C-11, art. 57"),
    _shared_theme("U15", "A5", 15, "Affichage public et publicité commerciale", "art. 58, 58.1"),
    _uni_theme("U16", 16, "Nom de l'entreprise en français", "art. 63-68.1",
        ("Le nom d'une entreprise doit être en langue française (art. 63). Un nom en langue française "
         "est nécessaire à l'obtention de la personnalité juridique (art. 64). Le nom peut être assorti "
         "d'une version dans une autre langue pourvu que, dans son utilisation, le nom de langue "
         "française figure de façon au moins aussi évidente (art. 68)."),
        "Charte de la langue française, RLRQ c. C-11, art. 63 à 68.1"),
    # ---- Hors périmètre d'amorce (marginaux) : inclus mais non prioritaires.
    # Textes non fournis intégralement → texte_loi_valide = False (prudence).
    _uni_theme("U17", 17, "Inscriptions sur les jouets et les jeux", "art. 54",
        ("Les jouets et les jeux visés par l'article 54 de la Charte, dont le fonctionnement exige "
         "l'emploi d'un vocabulaire autre que français, ne peuvent être offerts sur le marché à moins "
         "qu'une version française du jouet ou jeu ne soit disponible dans des conditions au moins "
         "aussi favorables."),
        "Charte de la langue française, RLRQ c. C-11, art. 54", prioritaire=False, valide=False),
    _uni_theme("U18", 18, "Contrats relatifs à un immeuble résidentiel", "art. 55.1",
        ("Certains contrats relatifs à un immeuble résidentiel sont visés par les règles de langue de "
         "l'article 55.1 de la Charte."),
        "Charte de la langue française, RLRQ c. C-11, art. 55.1", prioritaire=False, valide=False),
]


_PARCOURS_A_GATES = {
    "U3": "syndicat", "U7": "syndicat", "U8": "syndicat",
    "U4": "info_only", "U5": "info_only",
    "U10": "produits", "U11": "produits", "U14": "produits",
    "U17": "jouets", "U18": "immo",
}
for _t in UNIVERSAL_THEMES:
    _t["gate"] = _PARCOURS_A_GATES.get(_t["id"])


def themes_for_regime(regime):
    """Catalogue de thèmes consulté par le moteur selon le régime du dossier.
    Régime A (< 25 employés) : obligations universelles U1–U18.
    Régime B (25 employés et plus) : catalogue de francisation A1–A5 / B1–B9 (défaut)."""
    return UNIVERSAL_THEMES if regime == "A" else THEMES_LEGAUX


# ==================================================================
# Cadre légal du PARCOURS Régime A (< 25 employés).
# Une petite entreprise n'est pas suivie par l'Office SAUF plainte, mais elle demeure
# assujettie aux articles exécutoires. Les entreprises d'au moins 5 employés doivent en
# outre déclarer au registre (REQ) la proportion d'employés ne pouvant communiquer en
# français (art. 149 Charte + art. 33, 10° P-44.1). Sources vérifiées : texte_loi_valide=True.
# ==================================================================
REGIME_A_LEGAL_FRAMEWORK = [
    {"id": "C149", "article": "art. 149 (Charte)",
     "titre": "Offre de services d'apprentissage du français (entreprises d'au moins 5 employés)",
     "texte_loi": ("L'Office, après consultation de Francisation Québec, détermine annuellement, dans les "
                   "secteurs d'activités qu'il choisit, les entreprises assujetties à la Loi sur la publicité "
                   "légale des entreprises (chapitre P-44.1) qui emploient au moins cinq personnes, sans être "
                   "visées à l'article 139, auxquelles il offrira de mettre en place les services d'apprentissage "
                   "du français fournis par Francisation Québec conformément au chapitre VIII.2 du titre I. "
                   "L'Office avise l'entreprise concernée de l'offre qui lui est faite et du délai dont elle "
                   "dispose pour l'accepter et, le cas échéant, pour convenir avec Francisation Québec des "
                   "modalités selon lesquelles ces services seront fournis. L'Office transmet une copie de cet "
                   "avis à Francisation Québec."),
     "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 149", "texte_loi_valide": True},
    {"id": "C150", "article": "art. 150 (Charte)",
     "titre": "Accès des employés aux services d'apprentissage du français",
     "texte_loi": ("L'entreprise qui met en place des services d'apprentissage du français fournis par "
                   "Francisation Québec est tenue de permettre aux personnes à son emploi qui ne sont pas en "
                   "mesure de communiquer en français de recevoir ces services. L'article 137.1 s'applique à "
                   "ces personnes, compte tenu des adaptations nécessaires."),
     "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 150", "texte_loi_valide": True},
    {"id": "C151", "article": "art. 151 (Charte)",
     "titre": "Pouvoir d'exiger une analyse et un programme (entreprises de moins de 50 employés) — entente particulière",
     "texte_loi": ("Avec l'approbation du ministre de la Langue française, l'Office peut, à condition d'en "
                   "publier avis à la Gazette officielle du Québec, exiger d'une entreprise employant moins de "
                   "50 personnes qu'elle procède à l'analyse de sa situation linguistique, à l'élaboration et à "
                   "l'application d'un programme de francisation. Si une telle entreprise a besoin d'un délai "
                   "pour se conformer à certaines dispositions, elle peut demander l'aide de l'Office et conclure "
                   "avec lui une entente particulière ; dans ce cadre, l'Office peut, pour la période qu'il "
                   "détermine, l'exempter de l'application de toute disposition de la loi ou d'un règlement."),
     "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 151", "texte_loi_valide": True},
    {"id": "C152_1", "article": "art. 152.1 (Charte)",
     "titre": "Contrats et subventions de l'Administration conditionnés au respect du processus",
     "texte_loi": ("L'Administration ne peut conclure un contrat avec une entreprise assujettie à la section II, "
                   "ni lui octroyer une subvention, lorsqu'elle ne possède pas d'attestation d'inscription, n'a "
                   "pas fourni dans le délai prescrit l'analyse de sa situation linguistique, ne possède pas "
                   "d'attestation d'application de programme ni de certificat, ou si son nom figure sur la liste "
                   "prévue à l'article 152. Elle ne peut non plus contracter avec une entreprise assujettie à la "
                   "section III qui a refusé l'offre faite en vertu de l'article 149 (à moins qu'elle n'ait par "
                   "la suite convenu de mettre en place les services) ou qui fait défaut de respecter les "
                   "modalités convenues avec Francisation Québec."),
     "external_citation": "Charte de la langue française, RLRQ c. C-11, art. 152.1", "texte_loi_valide": True},
    {"id": "P33_10", "article": "art. 33, 10° (P-44.1)",
     "titre": "Déclaration au registre — nombre de salariés au Québec et proportion ne pouvant communiquer en français",
     "texte_loi": ("La déclaration d'immatriculation de l'assujetti contient, le cas échéant, le nombre de "
                   "salariés de l'assujetti dont le lieu de travail est situé au Québec, selon la tranche "
                   "correspondante déterminée par le ministre, et, lorsque l'assujetti est une entreprise visée "
                   "au premier alinéa de l'article 149 de la Charte de la langue française (chapitre C-11), la "
                   "proportion de ceux-ci qui, le cas échéant, ne sont pas en mesure de communiquer en français."),
     "external_citation": "Loi sur la publicité légale des entreprises, RLRQ c. P-44.1, art. 33, 10°",
     "texte_loi_valide": True},
]


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
