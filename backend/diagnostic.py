"""Diagnostic d'ouverture du dossier (Phase 2).

Trois indices + un diagnostic d'admissibilité à une Entente particulière (EP, art. 144),
calculés à partir des données de l'amorce et du Module 1. Tout est une **estimation
indicative — à valider par un professionnel** ; on n'affirme jamais une conformité
définitive. Aucune couleur « problème » n'est utilisée pour l'EP ni pour la francisabilité :
ce sont des indicateurs de régime, pas des mesures de bien/mal.
"""

PRUDENCE = "Estimation indicative — à valider par un professionnel."
SEUIL_HORS_QUEBEC = 50  # % de revenus hors Québec (déterminant dans la loi)


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace("%", "").strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _pct_hors(m1, key):
    q = _num(m1.get(key))
    if q is None:
        return None
    return max(0.0, round(100.0 - q, 1))


def _oui(v):
    return isinstance(v, str) and v.strip().lower().startswith("oui")


# ----------------------------------------------------------------- Conformité
_FR_VALUES = {"oui", "en français seulement", "plus en français", "bilingue équivalent"}
_NON_FR_VALUES = {"non", "plus dans une autre langue", "dans une autre langue seulement"}


def _lang_status(v):
    if v is None or v == "" or str(v).strip().upper() == "S.O.":
        return "non_evalue"
    s = str(v).strip().lower()
    if s in _FR_VALUES:
        return "francais"
    if s in _NON_FR_VALUES:
        return "non_francais"
    return "non_evalue"


def _combine(*statuts):
    if "non_francais" in statuts:
        return "non_francais"
    if "francais" in statuts:
        return "francais"
    return "non_evalue"


def _logiciels_status(m1):
    rows = m1.get("s9.grille_apps") or []
    if not isinstance(rows, list) or not rows:
        return "non_evalue"
    any_non_fr = False
    any_fr = False
    for r in rows:
        if not isinstance(r, dict):
            continue
        users_autre = _num(r.get("users_autre"))
        version_fr = str(r.get("version_fr") or "").strip().lower()
        if (users_autre and users_autre > 0) or version_fr == "non":
            any_non_fr = True
        elif version_fr == "oui":
            any_fr = True
    if any_non_fr:
        return "non_francais"
    if any_fr:
        return "francais"
    return "non_evalue"


def compute_conformite(m1):
    elements = [
        {"key": "affichage_public", "label": "Affichage public", "important": True,
         "statut": _lang_status(m1.get("s8.e_publicite"))},
        {"key": "site_web_medias", "label": "Site web et médias sociaux", "important": True,
         "statut": _combine(_lang_status(m1.get("s8.e_site_web")), _lang_status(m1.get("s8.medias_sociaux")))},
        {"key": "logiciels", "label": "Langue des logiciels", "important": True,
         "statut": _logiciels_status(m1)},
        {"key": "etiquetage", "label": "Étiquetage et inscriptions sur les emballages", "important": False,
         "statut": _lang_status(m1.get("s8.e_inscriptions"))},
    ]
    non_conformes = sum(1 for e in elements if e["statut"] == "non_francais")
    evalues = sum(1 for e in elements if e["statut"] != "non_evalue")
    if evalues == 0:
        band = "non_evalue"
    elif non_conformes == 0:
        band = "vert"
    elif non_conformes >= 3:
        band = "rouge"
    else:
        band = "jaune"
    return {
        "band": band, "non_conformes": non_conformes,
        "evalues": evalues, "total": len(elements),
        "elements": elements,
        "note": "Vert : tous les éléments en français · Jaune : au moins un élément non conforme · Rouge : 3 éléments ou plus non conformes.",
    }


# ----------------------------------------------------------------- EP (art. 144)
def compute_ep(m1):
    rev_hors = _pct_hors(m1, "s3.pct_ca")
    etab_hors = m1.get("s4.etab_hors_quebec")
    siege_qc = m1.get("s4.siege_quebec")

    if _oui(etab_hors) or (isinstance(siege_qc, str) and siege_qc.strip().lower() == "non"):
        outside_ops = True
    elif (etab_hors in (None, "")) and (siege_qc in (None, "")):
        outside_ops = None
    else:
        outside_ops = False

    cond_rev = None if rev_hors is None else rev_hors > SEUIL_HORS_QUEBEC
    conditions = [
        {"label": f"Plus de {SEUIL_HORS_QUEBEC} % des revenus réalisés hors Québec (sur les 3 dernières années)",
         "ok": cond_rev,
         "detail": (f"{rev_hors:.0f} % hors Québec" if rev_hors is not None else "non renseigné")},
        {"label": "L'entreprise dirige des activités ou du personnel hors Québec",
         "ok": outside_ops,
         "detail": ("établissements ou siège hors Québec" if outside_ops
                    else ("aucun" if outside_ops is False else "non renseigné"))},
    ]

    if rev_hors is None or outside_ops is None:
        state, label = "a_determiner", "À déterminer"
        expl = "Données insuffisantes (revenus hors Québec et/ou activités hors Québec non renseignés)."
    elif cond_rev and outside_ops:
        state, label = "potentiellement_admissible", "Potentiellement admissible à une EP"
        expl = ("Les deux conditions de l'article 144 semblent réunies. L'admissibilité et les "
                "conditions exactes doivent être confirmées par un professionnel (données sur 3 ans).")
    else:
        state, label = "non_admissible", "Non admissible à une EP"
        expl = ("Régime général de francisation : les conditions de l'article 144 ne sont pas réunies "
                "(revenus hors Québec ≤ 50 % ou absence d'activités hors Québec).")
    return {"state": state, "label": label, "explication": expl, "conditions": conditions,
            "revenus_hors_quebec": rev_hors}


# ----------------------------------------------------------------- Francisabilité
def compute_francisabilite(m1, ep):
    facteurs = [
        {"label": "% du chiffre d'affaires hors Québec", "value": _pct_hors(m1, "s3.pct_ca"),
         "unit": "%", "principal": True,
         "note": "Facteur déterminant : le français ne peut être généralisé si la majorité des revenus est réalisée hors Québec."},
        {"label": "% de la clientèle hors Québec", "value": _pct_hors(m1, "s3.pct_clientele"),
         "unit": "%", "principal": False,
         "note": "Indicateur de clientèle non francophone potentielle."},
        {"label": "% des fournisseurs hors Québec", "value": _pct_hors(m1, "s3.pct_fournisseurs"),
         "unit": "%", "principal": False, "note": ""},
        {"label": "% des achats hors Québec", "value": _pct_hors(m1, "s3.pct_achats"),
         "unit": "%", "principal": False, "note": ""},
        {"label": "Établissements hors Québec", "value": ("Oui" if _oui(m1.get("s4.etab_hors_quebec"))
                   else ("Non" if m1.get("s4.etab_hors_quebec") else None)),
         "unit": "", "principal": False,
         "note": "L'entreprise travaille avec des collègues, partenaires, fournisseurs ou clients hors Québec."},
    ]
    return {
        "revenus_hors_quebec": _pct_hors(m1, "s3.pct_ca"),
        "seuil": SEUIL_HORS_QUEBEC,
        "facteurs": facteurs,
        "ep": ep,
        "note": ("La francisabilité décrit le régime linguistique de l'entreprise selon son ouverture "
                 "hors Québec — ce n'est pas une note de réussite ou d'échec."),
    }


# ----------------------------------------------------------------- Risque
def compute_risque(m1, employes, jours_restants, conformite, ep):
    score = 0
    facteurs = []
    band = conformite["band"]
    if band == "rouge":
        score += 2
        facteurs.append("Conformité linguistique faible (3+ éléments non conformes)")
    elif band == "jaune":
        score += 1
        facteurs.append("Au moins un élément non conforme")

    emp = employes or 0
    if emp >= 100:
        score += 2
        facteurs.append("100 employés ou plus : comité de francisation requis")
    elif emp >= 25:
        score += 1
        facteurs.append("25 à 99 employés : obligations de francisation accrues")

    if jours_restants is not None:
        if jours_restants < 0:
            score += 2
            facteurs.append("Échéance légale dépassée")
        elif jours_restants <= 30:
            score += 1
            facteurs.append("Échéance légale à moins de 30 jours")

    if score >= 3:
        niveau = "eleve"
    elif score >= 1:
        niveau = "modere"
    else:
        niveau = "faible"
        facteurs.append("Aucun facteur de risque majeur détecté")
    return {"niveau": niveau, "score": score, "facteurs": facteurs}


def compute_diagnostic(m1, employes, jours_restants):
    ep = compute_ep(m1)
    conformite = compute_conformite(m1)
    francisabilite = compute_francisabilite(m1, ep)
    risque = compute_risque(m1, employes, jours_restants, conformite, ep)
    return {
        "ep": ep,
        "francisabilite": francisabilite,
        "conformite": conformite,
        "risque": risque,
        "employes_quebec": employes,
        "jours_restants": jours_restants,
        "prudence": PRUDENCE,
    }
