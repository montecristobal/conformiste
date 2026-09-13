"""Capture d'écran d'une page Web via navigateur headless (Chrome/Chromium).

Utilisé pour joindre au dossier une preuve visuelle (langue affichée sur le site
Web ou les médias sociaux). Anti-SSRF : validation de l'URL avant capture.
"""
import os
import subprocess
import tempfile
import logging

from analysis import _validate_public_url

logger = logging.getLogger("conformiste.screenshot")

_CHROME = None
for _c in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
           "/root/bin/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
    if os.path.exists(_c):
        _CHROME = _c
        break


def capture_screenshot(url: str, timeout: int = 35) -> bytes:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    _validate_public_url(url)
    if not _CHROME:
        raise RuntimeError("Navigateur headless indisponible")
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "shot.png")
        cmd = [
            _CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--user-data-dir={tmp}/profile",
            "--window-size=1280,1600", "--virtual-time-budget=9000",
            f"--screenshot={out}", url,
        ]
        try:
            subprocess.run(cmd, timeout=timeout, capture_output=True)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Délai dépassé lors de la capture d'écran")
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            raise RuntimeError("Capture d'écran impossible")
        with open(out, "rb") as f:
            return f.read()
