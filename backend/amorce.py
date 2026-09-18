"""Amorce mobile — couplage QR, transcription vocale (Whisper) et traduction FR (GPT).

Approche légère native : uploads HTTP + clé Emergent, aucune dépendance externe.
La personne au téléphone répond de vive voix ; on transcrit dans la langue parlée
(Whisper), on traduit/normalise en français (GPT) pour préremplir le champ, et on
CONSERVE l'audio original intact (stocké comme document du dossier).
"""
import os
import io
import re
import logging

from openai import AsyncOpenAI

logger = logging.getLogger("conformiste.amorce")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4")
_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Les 5 questions de l'amorce (texte exact fourni par le client).
AMORCE_QUESTIONS = [
    {"key": "q1_neq", "field": "neq",
     "question": "Quel est le numéro d'entreprise du Québec, le NEQ, de votre entreprise?",
     "optional": False, "aide": ""},
    {"key": "q2_site", "field": "site_web",
     "question": "Avez-vous un site web? Si oui, quelle est l'adresse?",
     "optional": True,
     "aide": "Facultatif : si vous ne connaissez pas l'adresse exacte par cœur, répondez simplement « oui » — vous la préciserez plus tard."},
    {"key": "q3_employes", "field": "nb_employes_quebec",
     "question": "Combien d'employés votre entreprise compte-t-elle au Québec?",
     "optional": False, "aide": ""},
    {"key": "q4_ca_pct", "field": "ca_pct_quebec",
     "question": "Quel pourcentage de votre chiffre d'affaires est réalisé au Québec, et quel pourcentage est réalisé à l'extérieur du Québec?",
     "optional": False, "approximate": True,
     "aide": "Une réponse approximative suffit (ex. : « environ 70-30 ») — vous pourrez raffiner dans le formulaire complet."},
    {"key": "q5_etablissements", "field": "nb_etablissements",
     "question": "Combien d'établissements votre entreprise a-t-elle au Québec?",
     "optional": False, "aide": ""},
]

AMORCE_PHOTO_CATEGORIES = [
    {"key": "facade", "label": "Façade", "hint": "L'extérieur du bâtiment."},
    {"key": "enseigne", "label": "Enseigne", "hint": "L'enseigne commerciale visible de la rue."},
    {"key": "affichage_interieur", "label": "Affichage intérieur", "hint": "Affiches, menus, prix à l'intérieur."},
    {"key": "poste_travail", "label": "Poste de travail / écran de logiciel",
     "hint": "Un écran d'ordinateur ou de logiciel typique utilisé au travail."},
    {"key": "offre_emploi", "label": "Offre d'emploi affichée",
     "hint": "Une offre d'emploi actuellement affichée. Si aucune, indiquez-le explicitement."},
    {"key": "documents", "label": "Documents", "hint": "Contrats, factures, dépliants, etc."},
    {"key": "autre", "label": "Autre", "hint": "Tout autre élément pertinent."},
]

# --- Régime A (< 25 employés) : obligations universelles.
# On retire les questions vocales propres à la francisation (% CA hors Québec,
# établissements) qui n'ont pas de sens sous ce régime, et on cible des photos
# pertinentes pour les obligations universelles (produits, factures, menus…).
AMORCE_QUESTIONS_A = [q for q in AMORCE_QUESTIONS if q["key"] in ("q1_neq", "q2_site", "q3_employes")]

AMORCE_PHOTO_CATEGORIES_A = [
    {"key": "facade", "label": "Façade", "hint": "L'extérieur du bâtiment."},
    {"key": "enseigne", "label": "Enseigne", "hint": "L'enseigne commerciale visible de la rue."},
    {"key": "affichage_interieur", "label": "Affichage intérieur", "hint": "Affiches, prix à l'intérieur."},
    {"key": "produits_emballages", "label": "Produits / emballages",
     "hint": "Étiquettes, emballages, modes d'emploi, certificats de garantie."},
    {"key": "menus", "label": "Menus / carte des vins", "hint": "Menus et cartes des vins, le cas échéant."},
    {"key": "factures", "label": "Factures / reçus", "hint": "Factures, reçus, contrats types, dépliants."},
    {"key": "autre", "label": "Autre", "hint": "Tout autre élément pertinent."},
]

# Catégories de photos auto-analysées par la vision LLM en tâche de fond.
AMORCE_ANALYZE_CATS = {
    "facade", "enseigne", "affichage_interieur", "poste_travail", "offre_emploi",
    "produits_emballages", "menus", "factures", "documents",
}


def questions_for_regime(regime):
    return AMORCE_QUESTIONS_A if regime == "A" else AMORCE_QUESTIONS


def photo_categories_for_regime(regime):
    return AMORCE_PHOTO_CATEGORIES_A if regime == "A" else AMORCE_PHOTO_CATEGORIES

_CT_EXT = {
    "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp",
    "image/heic": "heic", "image/heif": "heif",
    "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/x-m4a": "m4a",
    "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/x-wav": "wav",
    "video/webm": "webm",
}


def ext_from_content_type(ct: str, default: str = "bin") -> str:
    return _CT_EXT.get((ct or "").split(";")[0].strip().lower(), default)


async def transcribe_audio(data: bytes, filename: str):
    """Transcrit l'audio dans la langue parlée (Whisper). Retourne (texte, langue)."""
    bio = io.BytesIO(data)
    bio.name = filename or "audio.webm"
    resp = await _client.audio.transcriptions.create(
        model="whisper-1", file=bio, response_format="verbose_json")
    text = (getattr(resp, "text", "") or "").strip()
    lang = getattr(resp, "language", None)
    return text, lang


_TR_SYSTEM = (
    "Tu assistes un logiciel de conformité à la Charte de la langue française du Québec. "
    "On te donne la transcription d'une réponse ORALE à une question précise. "
    "Traduis fidèlement la réponse en français si elle est dans une autre langue, puis "
    "normalise-la en une réponse claire et concise. N'INVENTE RIEN et n'ajoute aucune "
    "information absente de la transcription. Si la personne dit ne pas savoir, conserve ce sens. "
    "Réponds UNIQUEMENT par la réponse en français, sans préambule ni guillemets."
)


async def translate_to_french(text: str, question: str) -> str:
    """Traduit/normalise la transcription en français pour préremplir le champ."""
    if not text:
        return ""
    try:
        resp = await _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": _TR_SYSTEM},
                      {"role": "user", "content": f"Question : {question}\nRéponse transcrite : {text}"}])
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning(f"amorce translate failed: {e}")
        return text


# Report des réponses vocales vers le Module 1 (analyse linguistique).
# On mappe chaque question de l'amorce vers la clé exacte du schéma Module 1
# et on extrait une valeur exploitable selon le type de champ.
AMORCE_M1_MAP = {
    "q1_neq": {"key": "s1.neq", "label": "NEQ", "kind": "neq"},
    "q2_site": {"key": "s1.sites_web", "label": "Site(s) web", "kind": "url"},
    "q3_employes": {"key": "s4.employes_quebec", "label": "Nombre d'employés au Québec", "kind": "int"},
    "q4_ca_pct": {"key": "s3.pct_ca", "label": "% du chiffre d'affaires au Québec", "kind": "percent"},
    "q5_etablissements": {"key": "s4.etablissements", "label": "Nombre d'établissements au Québec", "kind": "int"},
}


def _extract_value(kind: str, text: str):
    t = (text or "").strip()
    if not t:
        return None
    if kind == "neq":
        m = re.search(r"\d[\d\s.\-]{7,}\d", t)
        if m:
            digits = re.sub(r"\D", "", m.group(0))
            if 9 <= len(digits) <= 10:
                return digits
        return None
    if kind == "int":
        m = re.search(r"\d[\d\s]*", t)
        if m:
            d = re.sub(r"\D", "", m.group(0))
            return int(d) if d else None
        return None
    if kind == "percent":
        # première valeur en pourcentage (portion Québec, énoncée en premier).
        m = re.search(r"(\d{1,3})\s*%", t) or re.search(r"(\d{1,3})", t)
        return int(m.group(1)) if m else None
    if kind == "url":
        m = re.search(r"(https?://[^\s]+|(?:www\.)?[\w-]+\.[a-z]{2,}(?:/[^\s]*)?)", t, re.I)
        return m.group(0).rstrip(".,;") if m else None
    return t or None


def build_module1_proposals(answers: dict):
    """À partir des réponses vocales stockées, produit des propositions accept/refus."""
    out = []
    for qkey, spec in AMORCE_M1_MAP.items():
        a = (answers or {}).get(qkey)
        if not a:
            continue
        text = a.get("transcript_fr") or a.get("transcript_original") or ""
        val = _extract_value(spec["kind"], text)
        if val in (None, ""):
            continue
        lang = a.get("lang") or "?"
        out.append({
            "key": spec["key"], "label": spec["label"], "value": val,
            "source": "entrevue vocale (amorce)", "confidence": None,
            "note": f"Réponse orale ({lang}) : « {text} »",
        })
    return out
