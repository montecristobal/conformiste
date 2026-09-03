"""CONFORMISTE — vérification des CORRECTIFS du rapport iteration_3.

Couvre :
- I/O non bloquante (run_in_threadpool) : analyse lente + requête légère concurrente
- Verrouillage anti-force-brute (clé = email seul) + réinitialisation après succès
- Anti-SSRF sur les URL analysées
- 502 générique (pas de fuite d'exception)
- Validation des téléversements (extension + taille)
- DELETE /documents/{id} (soft-delete)
- Stabilité de echeance_suggeree (persistée)
- Non-régression : principe de prudence (aucun 'non_conforme')
"""
import io
import os
import re
import time
import uuid
import threading
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def admin_credentials():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not e or not pw:
        pytest.skip("no creds parsed")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="module")
def client(admin_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=admin_credentials)
    if r.status_code != 200:
        pytest.fail(f"admin login failed {r.status_code}: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    s.cookies.clear()
    return s


@pytest.fixture(scope="module")
def dossier(client):
    r = client.post(f"{API}/dossiers", json={
        "nom_entreprise": "TEST_Fixes I4 Inc.", "neq": "1140004444",
        "nb_employes_quebec": 42, "nb_etablissements": 1,
        "date_attestation_inscription": "2026-02-01"})
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _png_bytes(text_lines=("EMPLOYEE NOTICE", "ENGLISH ONLY", "STAFF MEETING 5PM")):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (700, 400), (245, 245, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 690, 390], outline=(20, 20, 60), width=6)
    y = 70
    for line in text_lines:
        d.text((50, y), line, fill=(10, 10, 10))
        y += 60
    for i in range(0, 700, 40):
        d.line([(i, 380), (i + 20, 350)], fill=(120, 120, 120), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- I/O non bloquante
class TestNonBlockingIO:
    """HIGH corrigé : run_in_threadpool sur les appels synchrones."""

    def test_light_request_during_slow_analysis(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "https://httpbin.org/delay/6"})
        assert r.status_code == 200, r.text[:300]
        doc_id = r.json()["id"]

        holder = {}

        def _analyze():
            try:
                holder["resp"] = client.post(f"{API}/documents/{doc_id}/analyze", timeout=120)
            except Exception as exc:  # noqa: BLE001
                holder["err"] = str(exc)

        t = threading.Thread(target=_analyze)
        t.start()
        time.sleep(1.5)  # analyse en cours (fetch bloquant de 6 s)

        latencies = []
        for _ in range(3):
            t0 = time.time()
            probe = client.get(f"{API}/catalogue/themes", timeout=30)
            latencies.append(time.time() - t0)
            assert probe.status_code == 200
            assert isinstance(probe.json(), list) and len(probe.json()) > 0
            time.sleep(0.4)

        t.join(timeout=150)
        worst = max(latencies)
        print(f"latences concurrentes GET /catalogue/themes: {latencies}")
        assert worst < 1.0, f"API bloquée pendant l'analyse (pire latence {worst:.2f}s) — latences={latencies}"

        # nettoyage
        client.delete(f"{API}/documents/{doc_id}")


# ---------------------------------------------------------------- brute force
class TestBruteForceLockout:
    """HIGH corrigé : compteur indexé sur l'email seul."""

    def test_lockout_after_five_failures(self):
        s = requests.Session()
        email = f"TEST_lock_{uuid.uuid4().hex[:8]}@example.com"
        codes = []
        for _ in range(6):
            r = s.post(f"{API}/auth/login", json={"email": email, "password": "WrongPass1!"})
            codes.append(r.status_code)
        print(f"codes lockout: {codes}")
        assert codes[:5] == [401] * 5, f"attendu 5x401, obtenu {codes}"
        assert codes[5] == 429, f"attendu 429 à la 6e tentative, obtenu {codes[5]}"
        body = s.post(f"{API}/auth/login", json={"email": email, "password": "WrongPass1!"})
        assert body.status_code == 429
        assert "tentatives" in body.json().get("detail", "").lower()

    def test_successful_login_resets_counter(self, admin_credentials):
        s = requests.Session()
        for i in range(4):
            r = s.post(f"{API}/auth/login",
                       json={"email": admin_credentials["email"], "password": "TotallyWrong1!"})
            assert r.status_code == 401, f"tentative {i+1} → {r.status_code}"

        ok = s.post(f"{API}/auth/login", json=admin_credentials)
        assert ok.status_code == 200, ok.text[:200]
        assert ok.json().get("access_token")

        # compteur remis à zéro : 4 nouveaux échecs ne doivent pas verrouiller
        for i in range(4):
            r = s.post(f"{API}/auth/login",
                       json={"email": admin_credentials["email"], "password": "TotallyWrong1!"})
            assert r.status_code == 401, (
                f"compteur non réinitialisé après succès : échec {i+1} → {r.status_code}")

        # remise à zéro finale pour ne pas gêner les autres tests
        final = s.post(f"{API}/auth/login", json=admin_credentials)
        assert final.status_code == 200


# ---------------------------------------------------------------- SSRF + 502
class TestUrlSecurity:
    """MEDIUM corrigé : anti-SSRF + message d'erreur générique."""

    @pytest.mark.parametrize("bad_url", [
        "http://127.0.0.1:8001/api/catalogue/themes",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://192.168.1.1/admin",
        "http://localhost:8001/api/auth/me",
    ])
    def test_internal_urls_rejected(self, client, dossier, bad_url):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url", json={"url": bad_url})
        assert r.status_code == 200, r.text[:300]
        doc_id = r.json()["id"]
        a = client.post(f"{API}/documents/{doc_id}/analyze", timeout=90)
        assert a.status_code == 400, f"{bad_url} → {a.status_code}: {a.text[:200]}"
        detail = a.json().get("detail", "")
        assert ("réseau interne" in detail) or ("Hôte introuvable" in detail), detail
        client.delete(f"{API}/documents/{doc_id}")

    def test_scheme_rejected(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "file:///etc/passwd"})
        assert r.status_code == 200
        doc_id = r.json()["id"]
        a = client.post(f"{API}/documents/{doc_id}/analyze", timeout=90)
        assert a.status_code == 400, f"{a.status_code}: {a.text[:200]}"
        client.delete(f"{API}/documents/{doc_id}")

    def test_502_does_not_leak_exception(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "https://httpbin.org/status/500"})
        doc_id = r.json()["id"]
        a = client.post(f"{API}/documents/{doc_id}/analyze", timeout=120)
        assert a.status_code == 502, f"attendu 502, obtenu {a.status_code}: {a.text[:200]}"
        body = a.text
        for leak in ("Traceback", "HTTPSConnectionPool", "NameResolutionError", "127.0.0.1", "pdfplumber"):
            assert leak not in body, f"fuite d'information: {body[:300]}"
        if "application/json" in (a.headers.get("content-type") or ""):
            detail = a.json().get("detail", "")
            assert detail == "L'analyse du document a échoué. Veuillez réessayer plus tard.", detail
        else:
            # L'edge (Cloudflare) remplace toute réponse 502 de l'origine par sa propre page HTML
            # « 502 Bad gateway » : le detail générique de l'API n'atteint jamais le client.
            print(f"NOTE: 502 intercepté par l'edge (content-type={a.headers.get('content-type')})")
        client.delete(f"{API}/documents/{doc_id}")


# ---------------------------------------------------------------- upload validation
class TestUploadValidation:
    """MEDIUM corrigé : extension + taille."""

    def test_reject_txt(self, client, dossier):
        files = {"file": ("TEST_notes.txt", b"hello world", "text/plain")}
        r = requests.post(f"{API}/dossiers/{dossier['id']}/documents", files=files,
                          headers={"Authorization": client.headers["Authorization"]})
        assert r.status_code == 400, f"{r.status_code}: {r.text[:200]}"
        assert "non autorisé" in r.json().get("detail", "")

    def test_reject_exe(self, client, dossier):
        files = {"file": ("TEST_payload.exe", b"MZ\x90\x00", "application/octet-stream")}
        r = requests.post(f"{API}/dossiers/{dossier['id']}/documents", files=files,
                          headers={"Authorization": client.headers["Authorization"]})
        assert r.status_code == 400, f"{r.status_code}: {r.text[:200]}"

    def test_reject_oversize(self, client, dossier):
        big = b"%PDF-1.4\n" + b"0" * (16 * 1024 * 1024)
        files = {"file": ("TEST_big.pdf", big, "application/pdf")}
        r = requests.post(f"{API}/dossiers/{dossier['id']}/documents", files=files,
                          headers={"Authorization": client.headers["Authorization"]}, timeout=180)
        assert r.status_code == 400, f"{r.status_code}: {r.text[:200]}"
        assert "volumineux" in r.json().get("detail", "").lower()

    def test_accept_png(self, client, dossier):
        files = {"file": ("TEST_affiche.png", _png_bytes(), "image/png")}
        r = requests.post(f"{API}/dossiers/{dossier['id']}/documents", files=files,
                          headers={"Authorization": client.headers["Authorization"]})
        assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
        d = r.json()
        assert d["kind"] == "image"
        assert d["original_filename"] == "TEST_affiche.png"
        assert d["size"] > 0
        assert "_id" not in d
        # round-trip download
        dl = client.get(f"{API}/documents/{d['id']}/download")
        assert dl.status_code == 200
        assert dl.content[:4] == b"\x89PNG"
        client.delete(f"{API}/documents/{d['id']}")


# ---------------------------------------------------------------- delete + plan
class TestDeleteAndPlan:
    """LOW corrigé : soft-delete + échéance persistée. Non-régression prudence."""

    def test_soft_delete_removes_from_list(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "https://example.com"})
        doc_id = r.json()["id"]
        lst = client.get(f"{API}/dossiers/{dossier['id']}/documents").json()
        assert any(d["id"] == doc_id for d in lst)

        dele = client.delete(f"{API}/documents/{doc_id}")
        assert dele.status_code == 200, dele.text[:200]
        assert dele.json().get("ok") is True

        lst2 = client.get(f"{API}/dossiers/{dossier['id']}/documents").json()
        assert not any(d["id"] == doc_id for d in lst2), "document toujours listé après suppression"

    def test_deleted_document_no_longer_addressable(self, client, dossier):
        """get_owned_document ne filtre pas is_deleted : un document supprimé reste
        téléchargeable / analysable / re-supprimable (échec attendu — à corriger)."""
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "https://example.com"})
        doc_id = r.json()["id"]
        assert client.delete(f"{API}/documents/{doc_id}").status_code == 200
        again = client.delete(f"{API}/documents/{doc_id}")
        assert again.status_code == 404, (
            f"document supprimé encore adressable (DELETE → {again.status_code})")

    def test_analysis_prudence_and_stable_echeance(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "https://example.com"})
        doc_id = r.json()["id"]
        a = client.post(f"{API}/documents/{doc_id}/analyze", timeout=180)
        assert a.status_code == 200, f"{a.status_code}: {a.text[:300]}"
        ana = a.json()["analysis"]
        assert ana["langue_detectee"] in ("francais", "autre", "mixte")
        assert isinstance(ana["elements"], list)
        for el in ana["elements"]:
            assert el["statut"] == "a_valider", f"PRUDENCE violée: {el}"
            assert "echeance_suggeree_date" in el

        p1 = client.get(f"{API}/dossiers/{dossier['id']}/plan-correction")
        assert p1.status_code == 200
        items1 = p1.json()
        assert all(i["statut"] == "a_valider" for i in items1)
        assert all(i["texte_loi_valide"] is False for i in items1)

        time.sleep(1)
        items2 = client.get(f"{API}/dossiers/{dossier['id']}/plan-correction").json()
        m1 = {i["finding_id"]: i["echeance_suggeree"] for i in items1}
        m2 = {i["finding_id"]: i["echeance_suggeree"] for i in items2}
        assert m1 == m2, f"échéances instables: {m1} vs {m2}"
        print(f"plan: {len(items1)} élément(s), échéances={list(m1.values())}")
        client.delete(f"{API}/documents/{doc_id}")

    def test_courriel_draft_both_modules(self, client, dossier):
        for module in ("1", "2"):
            r = client.get(f"{API}/dossiers/{dossier['id']}/courriel?module={module}")
            assert r.status_code == 200, r.text[:200]
            d = r.json()
            assert d.get("subject") and d.get("body") and d.get("pdf_path")
            assert "non conforme" not in d["body"].lower()

    def test_audit_journal(self, client, dossier):
        r = client.get(f"{API}/dossiers/{dossier['id']}/audit")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) > 0
        actions = [x["action"] for x in rows]
        assert any("Suppression d'un document" in a for a in actions), actions[:10]
        assert all("_id" not in x for x in rows)
