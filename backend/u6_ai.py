"""Outil U6 — aide IA à la RÉDACTION du motif d'offre (art. 46, al. 2).

Ne produit JAMAIS de verdict de conformité. Aide uniquement à formuler, à partir des
faits déjà documentés par l'entreprise, un motif factuel à indiquer dans l'offre d'emploi.
"""
import os
from openai import AsyncOpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4")
_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_SYSTEM = (
    "Tu es un rédacteur au service d'une PME québécoise. À partir UNIQUEMENT des faits "
    "documentés fournis, tu rédiges en français un court motif (2 à 4 phrases) expliquant "
    "pourquoi la connaissance d'une autre langue que le français est requise pour ce poste, "
    "destiné à être indiqué dans l'offre d'emploi conformément à l'art. 46, al. 2 de la Charte "
    "de la langue française.\n"
    "RÈGLES STRICTES :\n"
    "- Tu ne portes AUCUN jugement de conformité, tu n'écris jamais que l'exigence est "
    "« justifiée », « conforme » ou « non conforme ».\n"
    "- Tu n'inventes aucun fait : utilise seulement les éléments fournis.\n"
    "- Ton neutre, factuel, concret. Pas de score, pas de pourcentage de conformité.\n"
    "- Réponds uniquement par le texte du motif, sans préambule."
)


async def draft_motif(poste: dict) -> str:
    s0 = poste or {}
    s1 = poste.get("section1", {}) or {}
    faits = {
        "titre_poste": s0.get("titre"),
        "langues_exigees": s0.get("langues_exigees"),
        "interlocuteurs_langue_autre": s1.get("interlocuteurs"),
        "frequence": s1.get("frequence"),
        "pourcentage_interlocuteurs_non_francophones": s1.get("pct_clientele_non_franco"),
        "nature_des_taches": s1.get("nature_taches"),
        "taches_necessitant_autre_langue": [
            t.get("texte") for t in (poste.get("description_tache", {}) or {}).get("tasks", [])
            if t.get("requires_other_lang")
        ],
    }
    user = ("Faits documentés (format JSON) :\n" + str(faits) +
            "\n\nRédige le motif à indiquer dans l'offre d'emploi.")
    resp = await _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": user}])
    return (resp.choices[0].message.content or "").strip()
