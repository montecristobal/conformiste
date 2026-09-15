"""Moteur d'analyse de non-conformité linguistique.

PRINCIPE DE PRUDENCE : ce module ne produit que des CONSTATS FACTUELS (niveau 1).
La qualification juridique (niveau 2) n'est affirmée que si le thème concerné a
`texte_loi_valide = True` — la décision est prise côté serveur, pas ici.
"""
import io
import os
import re
import json
import base64
import socket
import ipaddress
import logging
from urllib.parse import urlparse

import requests
import pdfplumber
from bs4 import BeautifulSoup

from openai import AsyncOpenAI

logger = logging.getLogger("conformiste.analysis")


class UrlValidationError(Exception):
    """URL rejetée (schéma non http/https, hôte interne/privé — anti-SSRF)."""


def _validate_public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlValidationError("URL invalide : seuls http et https sont autorisés.")
    host = parsed.hostname
    if not host:
        raise UrlValidationError("URL invalide.")
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        raise UrlValidationError("Hôte introuvable.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise UrlValidationError("Adresse non autorisée (réseau interne).")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4")
_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
MAX_TEXT = 12000


def extract_pdf_text(data: bytes) -> str:
    try:
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages[:20]:
                out.append(page.extract_text() or "")
        return "\n".join(out).strip()
    except Exception as e:
        logger.warning(f"PDF extract failed: {e}")
        return ""


def fetch_url_text(url: str) -> str:
    if not re.match(r"^https?://", url):
        url = "https://" + url
    _validate_public_url(url)
    headers = {"User-Agent": "Mozilla/5.0 (CONFORMISTE analyse)"}
    resp = requests.get(url, headers=headers, timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text.strip()


def _themes_catalogue_str(themes) -> str:
    return "\n".join(f"- {t['id']} : {t['nom_theme']}" for t in themes)


def _system_prompt(themes) -> str:
    return (
        "Tu es un assistant d'analyse linguistique pour la conformité à la Charte de la "
        "langue française du Québec (Loi 96). Tu travailles pour un logiciel professionnel.\n\n"
        "RÈGLE ABSOLUE — PRUDENCE JURIDIQUE :\n"
        "Tu ne produis QUE des CONSTATS FACTUELS vérifiables mécaniquement : la ou les langues "
        "présentes dans le contenu, la présence ou l'absence du français, et (pour une image) la "
        "prédominance visuelle relative du français si observable. Tu NE rends JAMAIS de verdict "
        "juridique définitif (« viole l'article X »). Tu peux seulement indiquer qu'un thème est "
        "POTENTIELLEMENT concerné. La qualification légale finale est décidée par le logiciel.\n\n"
        "Catalogue des thèmes légaux (utilise EXACTEMENT ces identifiants) :\n"
        f"{_themes_catalogue_str(themes)}\n\n"
        "Tu réponds STRICTEMENT en JSON valide (aucun texte hors du JSON), au format :\n"
        "{\n"
        '  "langue_detectee": "francais" | "autre" | "mixte",\n'
        '  "resume": "courte description factuelle du contenu analysé",\n'
        '  "elements": [\n'
        "    {\n"
        '      "theme_id": "<un id du catalogue>",\n'
        '      "constat": "constat factuel précis (ex: le texte est uniquement en anglais)",\n'
        '      "potentiellement_non_conforme": true | false,\n'
        '      "mesure_suggeree": "suggestion de correction (présentée comme piste, pas obligation)",\n'
        '      "echeance_suggeree_jours": <entier ou null>,\n'
        '      "cout_approximatif": "chaîne vide si non estimable — n\'invente aucun chiffre"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Si aucun élément pertinent n'est détecté, renvoie une liste elements vide. "
        "Rédige tous les textes en français."
    )


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        raw = m.group(0)
    return json.loads(raw)


async def run_llm_analysis(kind: str, payload, themes, filename: str = "") -> dict:
    """kind: 'image' (payload=base64 str + mime), 'text' (payload=str). Returns parsed dict."""
    if kind == "image":
        b64, mime = payload
        user_content = [
            {"type": "text",
             "text": ("Analyse cette image (photo d'affichage, de document ou de publicité). "
                      "Fais l'OCR du texte visible, détecte la ou les langues, et retourne le JSON demandé. "
                      "Considère notamment les thèmes d'affichage/publicité et de communications.")},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
    else:
        text = (payload or "")[:MAX_TEXT]
        if not text:
            return {"langue_detectee": "autre", "resume": "Aucun contenu textuel extrait.", "elements": []}
        user_content = ("Analyse le contenu textuel suivant et retourne le JSON demandé "
                        "(langue détectée, constats factuels, thèmes potentiellement concernés).\n\n"
                        f"--- CONTENU ---\n{text}")

    resp = await _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": _system_prompt(themes)},
                  {"role": "user", "content": user_content}])
    raw = resp.choices[0].message.content or ""
    try:
        data = _parse_json(raw)
    except Exception as e:
        logger.warning(f"JSON parse failed: {e}; raw={raw[:200]}")
        data = {"langue_detectee": "autre",
                "resume": "Analyse effectuée mais réponse non structurée.",
                "elements": []}
    data.setdefault("langue_detectee", "autre")
    data.setdefault("resume", "")
    data.setdefault("elements", [])
    valid_ids = {t["id"] for t in themes}
    data["elements"] = [e for e in data["elements"] if e.get("theme_id") in valid_ids]
    return data
