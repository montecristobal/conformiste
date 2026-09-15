"""Envoi de courriels transactionnels via l'API Resend (appel direct).

Voir RESEND_EMAIL_PLAYBOOK. `_assert_safe_email` est un garde-fou (G2/G3) copié
tel quel : à appeler sur CHAQUE envoi. Les destinataires viennent d'enregistrements
serveur, les corps de messages de gabarits serveur (jamais d'entrée appelant).
"""
import os
import re
import ipaddress
import logging
import httpx
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

logger = logging.getLogger("conformiste.mailer")

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "CONFORMISTE")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str) -> str | None:
    _assert_safe_email(subject, html)
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY manquant — courriel non envoyé.")
        return None
    payload = {"from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>", "to": [to],
               "subject": subject, "html": html}
    if EMAIL_REPLY_TO:
        payload["reply_to"] = EMAIL_REPLY_TO
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(RESEND_API_URL,
                                 headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                                          "Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


async def send_reminder_email(to: str, dossier_nom: str, message: str, dossier_id: str) -> str | None:
    app_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{app_url}/dossier/{dossier_id}" if app_url.startswith("https://") else None
    subject = f"Rappel d'échéance — {escape(dossier_nom)}"
    btn = (f'<p style="margin:20px 0"><a href="{escape(link)}" '
           f'style="background:#0F2B48;color:#fff;padding:10px 18px;border-radius:8px;'
           f'text-decoration:none;font-family:Arial,sans-serif;font-size:14px">'
           f'Ouvrir le dossier</a></p>') if link else ""
    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;'
        f'font-family:Arial,sans-serif;color:#0F172A">'
        f'<h2 style="color:#0F2B48;font-size:18px;margin:0 0 12px">Rappel d\'échéance légale</h2>'
        f'<p style="font-size:14px;line-height:1.5">Dossier : <strong>{escape(dossier_nom)}</strong></p>'
        f'<p style="font-size:14px;line-height:1.5">{escape(message)}</p>'
        f'{btn}'
        f'<p style="font-size:12px;color:#888;margin-top:24px">Envoyé par {escape(EMAIL_FROM_NAME)}, '
        f'votre outil de conformité à la Charte de la langue française. '
        f'Nous ne demandons jamais votre mot de passe par courriel.</p>'
        f'</td></tr></table>'
    )
    return await send_email(to=to, subject=subject, html=html)
