"""Iteration 5 tests: /api/v1 versioning, cron reminders, notifications, passive CLF-Expert fields."""
import base64
import io
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
V1 = f"{BASE_URL}/api/v1"
CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET") or backend_env.get("WEBHOOK_CRON_SECRET")

EXTERNAL_FIELDS = ["external_legal_object_id", "external_source_type", "external_version_id",
                   "external_citation", "reference_date", "retrieved_at"]


@pytest.fixture(scope="session")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not e or not pw:
        pytest.skip("no creds parsed")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    r = s.post(f"{V1}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("access_token")
    assert tok, "no access_token in login response"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# ---------------- API versioning ----------------
class TestVersioning:
    def test_login_under_v1(self, creds):
        r = requests.post(f"{V1}/auth/login", json=creds, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == creds["email"]

    def test_me_under_v1(self, client):
        r = client.get(f"{V1}/auth/me", timeout=30)
        assert r.status_code == 200
        assert "email" in r.json()

    def test_old_unversioned_prefix_gone(self, client):
        r = client.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 404, f"old /api prefix still served: {r.status_code}"

    def test_core_endpoints_v1(self, client):
        for path in ["/dossiers", "/clients", "/catalogue/themes", "/catalogue/stages", "/notifications"]:
            r = client.get(f"{V1}{path}", timeout=30)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"


# ---------------- passive CLF-Expert fields ----------------
class TestPassiveFields:
    def test_themes_have_external_fields(self, client):
        r = client.get(f"{V1}/catalogue/themes", timeout=30)
        assert r.status_code == 200
        themes = r.json()
        assert isinstance(themes, list) and len(themes) > 0
        for t in themes:
            assert t.get("texte_loi_valide") is False, f"{t.get('id')} texte_loi_valide={t.get('texte_loi_valide')}"
            for f in EXTERNAL_FIELDS:
                assert f in t, f"theme {t.get('id')} missing {f}"
                assert t[f] is None, f"theme {t.get('id')} {f} should be null, got {t[f]}"


# ---------------- cron reminders ----------------
class TestCronReminders:
    def test_cron_without_auth_401(self):
        r = requests.post(f"{V1}/cron/reminders", timeout=30)
        assert r.status_code == 401, r.text[:200]

    def test_cron_wrong_secret_401(self):
        r = requests.post(f"{V1}/cron/reminders", headers={"Authorization": "Bearer wrong"}, timeout=30)
        assert r.status_code == 401

    def test_cron_with_secret_accepted_and_generates(self, client):
        assert CRON_SECRET, "WEBHOOK_CRON_SECRET not configured"
        r = requests.post(f"{V1}/cron/reminders",
                          headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json() == {"status": "accepted"}
        import time
        time.sleep(4)
        notifs = client.get(f"{V1}/notifications", timeout=30).json()
        assert isinstance(notifs, list)
        assert len(notifs) > 0, "no notifications generated for owner"
        for n in notifs:
            assert n["type"] in ("j30", "j7", "retard")
            assert "_id" not in n
            assert n["message"]
            assert n["dossier_id"]

    def test_cron_idempotent(self, client):
        before = client.get(f"{V1}/notifications", timeout=30).json()
        r = requests.post(f"{V1}/cron/reminders",
                          headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=30)
        assert r.status_code == 200
        import time
        time.sleep(4)
        after = client.get(f"{V1}/notifications", timeout=30).json()
        keys_before = {(n["dossier_id"], n["type"]) for n in before}
        keys_after = {(n["dossier_id"], n["type"]) for n in after}
        assert keys_before == keys_after, "duplicate/new notifications created on second run"
        assert len(before) == len(after), f"count changed {len(before)} -> {len(after)}"

    def test_notification_type_matches_jours(self, client):
        notifs = client.get(f"{V1}/notifications", timeout=30).json()
        for n in notifs:
            j = n.get("jours")
            if j is None:
                continue
            if j < 0:
                assert n["type"] == "retard", n
            elif j <= 7:
                assert n["type"] == "j7", n
            elif j <= 30:
                assert n["type"] == "j30", n


class TestNotificationsCRUD:
    def test_mark_one_read(self, client):
        notifs = client.get(f"{V1}/notifications", timeout=30).json()
        if not notifs:
            pytest.skip("no notifications")
        target = notifs[0]
        r = client.post(f"{V1}/notifications/{target['id']}/read", timeout=30)
        assert r.status_code == 200
        again = client.get(f"{V1}/notifications", timeout=30).json()
        found = [n for n in again if n["id"] == target["id"]][0]
        assert found["read"] is True

    def test_read_all(self, client):
        r = client.post(f"{V1}/notifications/read-all", timeout=30)
        assert r.status_code == 200
        notifs = client.get(f"{V1}/notifications", timeout=30).json()
        assert all(n["read"] for n in notifs), "some notifications still unread after read-all"

    def test_notifications_require_auth(self):
        r = requests.get(f"{V1}/notifications", timeout=30)
        assert r.status_code in (401, 403)


# ---------------- non-regression: upload image + analyse + mesure ----------------
def _png_bytes():
    """Small PNG with real visual features (text-like blocks) built via PIL."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (420, 260), (245, 245, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 410, 250], outline=(20, 40, 80), width=4)
    d.rectangle([30, 40, 390, 90], fill=(220, 30, 40))
    d.text((50, 55), "WELCOME - SALE 50% OFF", fill=(255, 255, 255))
    d.text((50, 120), "OPEN DAILY 9AM-9PM", fill=(10, 10, 10))
    d.text((50, 160), "STORE ENTRANCE", fill=(10, 10, 10))
    for i in range(0, 400, 20):
        d.line([(30, 210 + (i % 30) // 10), (390, 215)], fill=(150, 150, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestNonRegression:
    @pytest.fixture(scope="class")
    def dossier(self, client):
        r = client.get(f"{V1}/dossiers", timeout=30)
        assert r.status_code == 200
        ds = r.json()
        if not ds:
            pytest.skip("no dossier available")
        return ds[0]

    def test_upload_image_and_thumbnail_download(self, client, dossier):
        content = _png_bytes()
        r = client.post(f"{V1}/dossiers/{dossier['id']}/documents",
                        files={"file": ("TEST_vitrine.png", content, "image/png")}, timeout=60)
        assert r.status_code in (200, 201), r.text[:300]
        doc = r.json()
        assert doc["kind"] == "image", f"kind should be image, got {doc.get('kind')}"
        assert "_id" not in doc
        did = doc["id"]
        # download must return image bytes (used by BlobThumb)
        dl = client.get(f"{V1}/documents/{did}/download", timeout=30)
        assert dl.status_code == 200
        assert dl.headers.get("content-type", "").startswith("image/"), dl.headers.get("content-type")
        assert dl.content[:8] == b"\x89PNG\r\n\x1a\n"
        # analyse
        an = client.post(f"{V1}/documents/{did}/analyze", timeout=180)
        assert an.status_code == 200, an.text[:500]
        res = an.json()
        analysis = res.get("analysis", res)
        elements = analysis.get("elements", [])
        assert isinstance(elements, list)
        for e in elements:
            assert e.get("statut") != "non_conforme", "prudence principle violated"
        client.delete(f"{V1}/documents/{did}", timeout=30)

    def test_url_document_keeps_url_kind(self, client, dossier):
        r = client.post(f"{V1}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "https://example.com", "label": "TEST_url"}, timeout=60)
        assert r.status_code in (200, 201), r.text[:300]
        doc = r.json()
        assert doc["kind"] == "url"
        client.delete(f"{V1}/documents/{doc['id']}", timeout=30)

    def test_plan_and_to_mesure_external_fields(self, client, dossier):
        r = client.get(f"{V1}/dossiers/{dossier['id']}/plan-correction", timeout=60)
        assert r.status_code == 200, r.text[:300]
        plan = r.json()
        findings = plan if isinstance(plan, list) else plan.get("findings", [])
        if not findings:
            pytest.skip("no findings in plan for this dossier")
        fid = findings[0].get("finding_id")
        assert fid, f"finding has no finding_id: {findings[0]}"
        m = client.post(f"{V1}/dossiers/{dossier['id']}/plan-correction/{fid}/to-mesure", timeout=60)
        assert m.status_code == 200, m.text[:300]
        mesure = m.json().get("mesure")
        assert mesure, f"no mesure returned: {str(m.json())[:300]}"
        for f in EXTERNAL_FIELDS:
            assert f in mesure, f"mesure missing {f}: {list(mesure.keys())}"
            assert mesure[f] is None, f"mesure {f} should be null"

    def test_courriel_draft(self, client, dossier):
        r = client.get(f"{V1}/dossiers/{dossier['id']}/courriel", params={"module": 1}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["subject"] and d["body"]
