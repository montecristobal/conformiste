"""Repeated image upload+analyse to measure flakiness of object-storage fetch (503)."""
import io
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/")
V1 = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def client():
    c = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*[-*]?\s*email\s*:\s*`?([^`\s]+)', c).group(1)
    pw = re.search(r'(?im)^\s*[-*]?\s*password\s*:\s*`?([^`\s]+)', c).group(1)
    s = requests.Session()
    r = s.post(f"{V1}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


def _png():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (480, 300), (250, 248, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 8, 470, 290], outline=(15, 43, 72), width=5)
    d.rectangle([40, 40, 430, 100], fill=(200, 25, 35))
    d.text((60, 65), "BIG SALE 50% OFF TODAY ONLY", fill=(255, 255, 255))
    d.text((60, 150), "OPEN MON-FRI 9:00-21:00", fill=(15, 15, 15))
    d.ellipse([340, 190, 430, 275], fill=(30, 90, 200))
    for i in range(60, 430, 16):
        d.line([(i, 230), (i + 8, 275)], fill=(160, 160, 160), width=2)
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def test_image_analysis_repeated(client):
    dossier = client.get(f"{V1}/dossiers", timeout=30).json()[0]
    results = []
    for i in range(3):
        up = client.post(f"{V1}/dossiers/{dossier['id']}/documents",
                         files={"file": (f"TEST_flaky_{i}.png", _png(), "image/png")}, timeout=60)
        assert up.status_code in (200, 201), up.text[:200]
        did = up.json()["id"]
        an = client.post(f"{V1}/documents/{did}/analyze", timeout=200)
        results.append(an.status_code)
        print(f"run {i}: analyze -> {an.status_code} {an.text[:120]}")
        client.delete(f"{V1}/documents/{did}", timeout=30)
    ok = results.count(200)
    print("IMAGE ANALYSIS RESULTS:", results, "success:", ok, "/", len(results))
    assert ok == len(results), f"image analysis flaky/failing: {results}"
