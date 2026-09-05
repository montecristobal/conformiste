"""Pré-remplissage du Module 1 (analyse linguistique) par recherche Web.

On parcourt le site Web officiel de l'entreprise (source réelle, protégée anti-SSRF)
puis un LLM (clé Emergent) PROPOSE des valeurs pour un ensemble restreint de champs
factuels. Le responsable accepte/refuse chaque proposition côté frontend.
Aucune valeur n'est écrite sans acceptation explicite.
"""
import os
import json
import logging
from urllib.parse import urlparse

from emergentintegrations.llm.chat import LlmChat, UserMessage
from analysis import fetch_url_text, _parse_json, UrlValidationError

logger = logging.getLogger("conformiste.enrichment")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
LLM_MODEL = ("openai", "gpt-5.4")
MAX_TEXT = 11000

# Champs ciblés : (clé module1 "sid.fid", libellé, type)
FIELDS = [
    ("s1.nom", "Nom de l'entreprise", "text"),
    ("s1.autres_noms", "Autre(s) nom(s) utilisé(s)", "text"),
    ("s1.sites_web", "Site(s) Web", "text"),
    ("s1.adresse", "Adresse (numéro, rue)", "text"),
    ("s1.ville", "Ville", "text"),
    ("s1.code_postal", "Code postal", "text"),
    ("s2.prenom", "Principal dirigeant — prénom", "text"),
    ("s2.nom", "Principal dirigeant — nom", "text"),
    ("s2.titre", "Principal dirigeant — titre de fonction", "text"),
    ("s3.activites", "Principales activités de l'entreprise", "text"),
    ("s3.competence_federale", "Entreprise de compétence fédérale", "oui_non"),
    ("s8.nom_affiche", "Nom d'entreprise affiché", "text"),
    ("s8.e_site_web", "Le(s) site(s) Web sont en français (8.14)", "oui_non_so"),
    ("s8.medias_sociaux", "Contenus publicitaires sur médias sociaux en français (8.15)", "oui_non"),
    ("s8.medias_sociaux_reseaux", "Principaux médias sociaux utilisés", "text"),
    ("s8.marques_autre_langue", "Marque(s) de commerce dans une autre langue (8.17)", "oui_non"),
    ("s11.prenom", "Représentant·e désigné·e — prénom", "text"),
    ("s11.nom", "Représentant·e désigné·e — nom", "text"),
    ("s11.fonction", "Représentant·e désigné·e — fonction", "text"),
]
_KINDS = {k: kind for k, _, kind in FIELDS}
_LABELS = {k: label for k, label, _ in FIELDS}


def _coerce(kind, value):
    if value is None:
        return None
    if kind == "text":
        s = str(value).strip()
        return s or None
    v = str(value).strip().lower()
    if kind in ("oui_non", "oui_non_so"):
        if v in ("oui", "yes", "true", "vrai", "1"):
            return "Oui"
        if v in ("non", "no", "false", "faux", "0"):
            return "Non"
        if kind == "oui_non_so" and v in ("s.o.", "so", "s.o", "n/a", "na"):
            return "S.O."
    return None


def _crawl(site_url):
    """Retourne (texte_concaténé, [urls_utilisées], [avertissements])."""
    warnings, used, chunks = [], [], []
    if not site_url:
        return "", used, ["Aucun site Web fourni : suggestions basées sur le nom seulement."]
    base = site_url if site_url.startswith(("http://", "https://")) else "https://" + site_url
    try:
        parsed = urlparse(base)
        root = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return "", used, [f"URL invalide : {site_url}"]

    candidates = [base]
    for path in ("/a-propos", "/about", "/nous-joindre", "/contact", "/entreprise"):
        candidates.append(root + path)

    for url in candidates:
        if len("".join(chunks)) > MAX_TEXT:
            break
        try:
            t = fetch_url_text(url)
            if t and len(t) > 60:
                chunks.append(f"\n[PAGE {url}]\n{t[:4000]}")
                used.append(url)
        except UrlValidationError as e:
            warnings.append(f"URL refusée ({url}) : {e}")
        except Exception:
            continue
    if not used:
        warnings.append("Le site Web n'a pas pu être parcouru (inaccessible ou protégé).")
    return "".join(chunks)[:MAX_TEXT], used, warnings


_SYSTEM = (
    "Tu es un assistant de recherche pour un logiciel de conformité à la Charte de la langue "
    "française du Québec. À partir du contenu réel d'un site Web d'entreprise et de faits publics "
    "notoires, tu PROPOSES des valeurs pour préremplir un formulaire d'analyse linguistique.\n\n"
    "RÈGLES :\n"
    "- Ne propose QUE des champs que tu peux appuyer sur le contenu fourni ou un fait public fiable. "
    "N'INVENTE JAMAIS. En cas de doute, omets le champ.\n"
    "- Pour les champs de langue (ex. site Web en français), déduis la langue à partir du texte fourni : "
    "français => 'Oui', uniquement une autre langue => 'Non', mixte/inconnu => omets.\n"
    "- Réponds STRICTEMENT en JSON valide, sans texte hors JSON, au format :\n"
    '{ "proposals": [ { "key": "<clé exacte>", "value": "<valeur>", '
    '"source": "site Web" | "déduction", "confidence": <0..1>, "note": "courte justification (fr)" } ] }\n'
    "- Rédige les textes en français."
)


async def enrich_module1(nom, neq, site_url):
    crawled, used, warnings = _crawl(site_url)
    champs = "\n".join(f'- "{k}" : {label} (type: {kind})' for k, label, kind in FIELDS)
    user_text = (
        f"Entreprise : {nom or '(inconnu)'} — NEQ : {neq or '(inconnu)'}\n"
        f"Site(s) fourni(s) : {site_url or '(aucun)'}\n\n"
        f"Champs à proposer (utilise EXACTEMENT ces clés) :\n{champs}\n\n"
        f"--- CONTENU DU SITE WEB (extraits réels) ---\n{crawled or '(aucun contenu récupéré)'}\n"
        "--- FIN ---\n\n"
        "Propose uniquement les champs appuyés par ce contenu ou un fait public fiable."
    )
    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"enrich-{neq or nom or 'ent'}",
        system_message=_SYSTEM,
    ).with_model(*LLM_MODEL)
    try:
        resp = await chat.send_message(UserMessage(text=user_text))
        data = _parse_json(resp)
    except Exception as e:
        logger.warning(f"enrich LLM/parse failed: {e}")
        data = {"proposals": []}

    out = []
    seen = set()
    for p in data.get("proposals", []):
        k = p.get("key")
        if k not in _KINDS or k in seen:
            continue
        val = _coerce(_KINDS[k], p.get("value"))
        if val in (None, ""):
            continue
        seen.add(k)
        src = p.get("source") or ("site Web" if used else "déduction")
        conf = p.get("confidence")
        try:
            conf = round(float(conf), 2)
        except (TypeError, ValueError):
            conf = None
        out.append({
            "key": k, "label": _LABELS[k], "value": val,
            "source": src, "confidence": conf, "note": (p.get("note") or "")[:200],
        })
    return {"proposals": out, "site_used": used, "warnings": warnings}
