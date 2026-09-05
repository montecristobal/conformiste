"""Pré-remplissage REQ — version DÉMO.

Génère un dossier d'entreprise réaliste et déterministe à partir d'un NEQ,
imitant la structure des données du Registraire des entreprises du Québec (REQ).
À remplacer par la vraie source (registre public temps réel ou données ouvertes
Données Québec) lors du branchement en production.
"""
import hashlib
from datetime import date, timedelta

_VILLES = [
    ("Montréal", "H2Y 1C6"), ("Québec", "G1R 4P5"), ("Laval", "H7T 2W3"),
    ("Gatineau", "J8X 2V6"), ("Longueuil", "J4H 3Y8"), ("Sherbrooke", "J1H 4M2"),
    ("Trois-Rivières", "G9A 1B4"), ("Saguenay", "G7H 5B8"),
]
_RUES = ["boul. René-Lévesque O.", "rue Sainte-Catherine O.", "boul. Saint-Laurent",
         "av. du Parc", "rue Notre-Dame O.", "boul. de Maisonneuve E.", "ch. de la Canardière"]
_FORMES = ["Société par actions (compagnie)", "Société en nom collectif",
           "Personne physique exploitant une entreprise individuelle",
           "Coopérative", "Société par actions de régime fédéral"]
_ACTIVITES = [
    ("541510", "Conception de systèmes informatiques et services connexes"),
    ("236220", "Construction de bâtiments commerciaux et institutionnels"),
    ("445110", "Supermarchés et autres épiceries"),
    ("722511", "Restaurants à service complet"),
    ("621110", "Cabinets de médecins"),
    ("561320", "Location de personnel suppléant"),
    ("311811", "Boulangeries de détail"),
    ("453998", "Autres magasins de détail divers"),
]
_PRENOMS = ["Marie", "Jean", "Sophie", "Luc", "Isabelle", "Pierre", "Nathalie",
            "François", "Julie", "Martin", "Caroline", "Éric"]
_NOMS = ["Tremblay", "Gagnon", "Roy", "Côté", "Bouchard", "Gauthier", "Morin",
         "Lavoie", "Fortin", "Gagné", "Ouellet", "Pelletier"]
_SUFFIXES = ["inc.", "ltée", "s.e.n.c.", "S.E.C.", "Corp."]
_MOTS = ["Groupe", "Solutions", "Technologies", "Boréal", "Saint-Laurent",
         "Horizon", "Nordik", "Fleuve", "Montcalm", "Cascades", "Érable", "Lumina"]


def _rng(neq: str):
    """Générateur pseudo-aléatoire déterministe basé sur le NEQ."""
    seed = int(hashlib.sha256((neq or "0").encode()).hexdigest(), 16)
    state = {"v": seed}

    def nxt(mod):
        state["v"] = (state["v"] * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        return state["v"] % mod
    return nxt


def _pick(nxt, lst):
    return lst[nxt(len(lst))]


def simulate_req(neq: str) -> dict:
    neq = (neq or "").strip()
    nxt = _rng(neq)

    nom = f"{_pick(nxt, _MOTS)} {_pick(nxt, _MOTS)} {_pick(nxt, _SUFFIXES)}"
    ville, cp = _pick(nxt, _VILLES)
    civique = 100 + nxt(9800)
    rue = _pick(nxt, _RUES)
    adresse_domicile = f"{civique}, {rue}, {ville} (Québec) {cp}"

    d0 = date(2005, 1, 1) + timedelta(days=nxt(7000))
    date_immat = d0.isoformat()
    date_maj = (d0 + timedelta(days=90 + nxt(3000))).isoformat()

    n_activites = 1 + nxt(3)
    acts = []
    seen = set()
    for _ in range(n_activites):
        code, desc = _pick(nxt, _ACTIVITES)
        if code in seen:
            continue
        seen.add(code)
        acts.append({"code_cae": code, "description": desc})

    n_admin = 1 + nxt(4)
    admins = []
    for i in range(n_admin):
        nom_pers = f"{_pick(nxt, _PRENOMS)} {_pick(nxt, _NOMS)}"
        role = "Président" if i == 0 else _pick(nxt, ["Administrateur", "Secrétaire", "Vice-président", "Trésorier"])
        admins.append({"nom": nom_pers, "fonction": role})

    n_etab = 1 + nxt(4)
    etabs = []
    for i in range(n_etab):
        v, c = _pick(nxt, _VILLES)
        etabs.append({
            "nom": nom if i == 0 else f"{nom} — Établissement {i + 1}",
            "adresse": f"{100 + nxt(9800)}, {_pick(nxt, _RUES)}, {v} (Québec) {c}",
            "principal": i == 0,
        })

    autres_noms = []
    if nxt(2):
        autres_noms.append(f"{_pick(nxt, _MOTS)} {_pick(nxt, _MOTS)}")

    nb_employes = _pick(nxt, [8, 22, 45, 60, 95, 120, 180, 260, 340])

    return {
        "source": "REQ (démonstration)",
        "neq": neq,
        "nom_entreprise": nom,
        "autres_noms": autres_noms,
        "forme_juridique": _pick(nxt, _FORMES),
        "statut_immatriculation": "Immatriculée",
        "etat": "En vigueur",
        "date_immatriculation": date_immat,
        "date_mise_a_jour_etat": date_maj,
        "regime_constitution": "Loi sur les sociétés par actions (Québec)",
        "adresse_domicile": adresse_domicile,
        "ville": ville,
        "code_postal": cp,
        "activites_economiques": acts,
        "administrateurs": admins,
        "etablissements": etabs,
        "nombre_etablissements": n_etab,
        "nombre_employes_estime": nb_employes,
    }
