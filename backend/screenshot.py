"""Capture d'écran d'une page Web via navigateur headless (Chrome/Chromium).

Utilisé pour joindre au dossier une preuve visuelle (langue affichée sur le site
Web ou les médias sociaux). Anti-SSRF : validation de l'URL avant capture.
"""
import os
import subprocess
import tempfile
import logging

from analysis import _validate_public_url
from io import BytesIO
from datetime import datetime, timezone

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None

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


def _font(size):
    import glob
    patterns = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/**/DejaVuSans*.ttf",
        "/usr/share/fonts/**/LiberationSans*.ttf",
        "/usr/share/fonts/**/NotoSans*.ttf",
        "/usr/share/fonts/**/Arimo*.ttf",
        "/usr/share/fonts/**/*.ttf",
    ]
    for pat in patterns:
        for p in sorted(glob.glob(pat, recursive=True)):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def stamp_proof(png_bytes: bytes, lines) -> bytes:
    """Incruste un bandeau d'authenticité (date + URL + langue) en haut de la capture."""
    if not Image:
        return png_bytes
    try:
        img = Image.open(BytesIO(png_bytes)).convert("RGB")
    except Exception:
        return png_bytes
    W, H = img.size
    pad, lh = 16, 30
    band = pad * 2 + lh * len(lines)
    canvas = Image.new("RGB", (W, H + band), (255, 255, 255))
    banner = Image.new("RGB", (W, band), (15, 43, 72))  # #0F2B48
    canvas.paste(banner, (0, 0))
    canvas.paste(img, (0, band))
    draw = ImageDraw.Draw(canvas)
    font = _font(21)
    y = pad
    for i, ln in enumerate(lines):
        draw.text((pad, y), ln, fill=(255, 255, 255) if i == 0 else (200, 214, 230), font=font)
        y += lh
    # trait de séparation
    draw.line([(0, band - 1), (W, band - 1)], fill=(212, 160, 23), width=3)
    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()
