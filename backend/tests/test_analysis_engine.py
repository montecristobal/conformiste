"""CONFORMISTE — tests du MOTEUR D'ANALYSE (documents, analyse LLM, plan de correction,
passerelle vers Module 2, brouillon de courriel, journal d'audit).

Point critique validé ici : PRINCIPE DE PRUDENCE — aucun constat ne doit avoir
statut 'non_conforme' tant que texte_loi_valide == False pour tous les thèmes.
"""
import io
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api/v1"


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
        "nom_entreprise": "TEST_Analyse Inc.", "neq": "1140000999",
        "nb_employes_quebec": 60, "nb_etablissements": 1,
        "date_attestation_inscription": "2026-01-15"})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d.get("id")
    yield d


def make_png_with_text() -> bytes:
    """Image PNG réelle avec du texte anglais visible (features visuelles, non uniforme)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (900, 420), (250, 248, 240))
    dr = ImageDraw.Draw(img)
    dr.rectangle([20, 20, 880, 400], outline=(20, 40, 120), width=6)
    dr.rectangle([40, 40, 300, 200], fill=(200, 30, 40))
    dr.line([300, 380, 880, 240], fill=(10, 100, 60), width=8)
    for i in range(0, 900, 40):
        dr.line([i, 0, i, 420], fill=(230, 228, 220), width=1)
    dr.text((80, 230), "BIG SALE - 50% OFF EVERYTHING", fill=(0, 0, 0))
    dr.text((80, 270), "OPEN 7 DAYS A WEEK - WELCOME", fill=(0, 0, 0))
    dr.text((80, 310), "STORE ENTRANCE - NO SMOKING", fill=(30, 30, 90))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_pdf_with_english_text() -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Helvetica", 14)
    c.drawString(70, 760, "EMPLOYEE HANDBOOK - INTERNAL COMMUNICATIONS")
    c.drawString(70, 730, "All staff memos and work documents are issued in English only.")
    c.drawString(70, 700, "Job postings are published in English on our careers website.")
    c.drawString(70, 670, "Invoices and commercial documents are provided in English.")
    c.showPage()
    c.save()
    return buf.getvalue()


VALIDATED_THEMES = {"A1", "A2", "A3", "A4", "A5"}  # textes de loi confirmés → verdict possible


def assert_prudence(elements):
    assert elements, "aucun élément détecté"
    for el in elements:
        assert el.get("statut") in ("a_valider", "non_conforme"), f"statut interdit: {el.get('statut')} ({el})"
        if el.get("theme_id") not in VALIDATED_THEMES:
            assert el.get("statut") == "a_valider", f"thème non validé doit rester prudent: {el}"
        assert el.get("id"), "élément sans id"
        assert el.get("converti") is False


# ------------------------------------------------- moteur d'analyse (séquentiel, une classe)
class TestMoteurAnalyse:
    # ---- réception de documents
    def test_add_url_document_and_list(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/documents/url",
                        json={"url": "example.com"})
        assert r.status_code == 200, r.text[:300]
        doc = r.json()
        assert doc["type"] == "url" and doc["kind"] == "url"
        assert doc["url"] == "example.com"
        assert doc["analysis"] is None
        assert "_id" not in doc
        pytest.url_doc_id = doc["id"]

        lst = client.get(f"{API}/dossiers/{dossier['id']}/documents")
        assert lst.status_code == 200
        ids = [d["id"] for d in lst.json()]
        assert doc["id"] in ids

    def test_upload_png_file(self, client, dossier):
        data = make_png_with_text()
        s = requests.Session()
        s.headers.update({"Authorization": client.headers["Authorization"]})
        r = s.post(f"{API}/dossiers/{dossier['id']}/documents",
                   files={"file": ("TEST_affichage.png", data, "image/png")})
        assert r.status_code == 200, r.text[:400]
        doc = r.json()
        assert doc["kind"] == "image"
        assert doc["content_type"] == "image/png"
        assert doc["size"] > 1000
        assert doc["storage_path"]
        pytest.img_doc_id = doc["id"]

        # download round-trip
        dl = client.get(f"{API}/documents/{doc['id']}/download")
        assert dl.status_code == 200, dl.text[:200]
        assert dl.content[:4] == b"\x89PNG"

    def test_upload_pdf_file(self, client, dossier):
        data = make_pdf_with_english_text()
        s = requests.Session()
        s.headers.update({"Authorization": client.headers["Authorization"]})
        r = s.post(f"{API}/dossiers/{dossier['id']}/documents",
                   files={"file": ("TEST_handbook.pdf", data, "application/pdf")})
        assert r.status_code == 200, r.text[:400]
        doc = r.json()
        assert doc["kind"] == "pdf"
        pytest.pdf_doc_id = doc["id"]

    def test_documents_require_auth(self, dossier):
        r = requests.get(f"{API}/dossiers/{dossier['id']}/documents")
        assert r.status_code == 401

    def test_documents_unknown_dossier_404(self, client):
        r = client.get(f"{API}/dossiers/does-not-exist/documents")
        assert r.status_code == 404


    # ---- analyse + prudence
    def test_analyze_url_english(self, client):
        doc_id = getattr(pytest, "url_doc_id", None)
        assert doc_id, "url doc missing"
        r = client.post(f"{API}/documents/{doc_id}/analyze", timeout=180)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        ana = d["analysis"]
        assert ana["langue_detectee"] in ("autre", "mixte"), ana["langue_detectee"]
        assert ana.get("resume")
        assert ana.get("analyzed_at")
        assert_prudence(ana["elements"])
        valid = {"A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3",
                 "B4", "B5", "B6", "B7", "B8", "B9"}
        for el in ana["elements"]:
            assert el["theme_id"] in valid

    def test_analyze_pdf_ocr_text(self, client):
        doc_id = getattr(pytest, "pdf_doc_id", None)
        assert doc_id, "pdf doc missing"
        r = client.post(f"{API}/documents/{doc_id}/analyze", timeout=240)
        assert r.status_code == 200, r.text[:500]
        ana = r.json()["analysis"]
        assert ana["langue_detectee"] in ("autre", "mixte"), ana
        assert_prudence(ana["elements"])

    def test_analyze_image_vision(self, client):
        doc_id = getattr(pytest, "img_doc_id", None)
        assert doc_id, "image doc missing"
        r = client.post(f"{API}/documents/{doc_id}/analyze", timeout=240)
        assert r.status_code == 200, r.text[:500]
        ana = r.json()["analysis"]
        assert "langue_detectee" in ana
        for el in ana.get("elements", []):
            assert el["statut"] in ("a_valider", "non_conforme")
            if el.get("theme_id") not in VALIDATED_THEMES:
                assert el["statut"] == "a_valider"

    def test_analyze_unknown_document(self, client):
        r = client.post(f"{API}/documents/unknown-id/analyze")
        assert r.status_code == 404


    # ---- plan de correction
    def test_plan_aggregates_findings(self, client, dossier):
        r = client.get(f"{API}/dossiers/{dossier['id']}/plan-correction")
        assert r.status_code == 200, r.text[:300]
        items = r.json()
        assert isinstance(items, list) and items
        for it in items:
            for k in ("finding_id", "document_id", "source", "theme_id", "theme_nom",
                      "constat", "statut", "mesure_suggeree", "echeance_suggeree",
                      "cout_approximatif", "converti", "texte_loi_valide"):
                assert k in it, f"champ manquant {k}"
            assert it["statut"] in ("a_valider", "non_conforme"), f"statut interdit: {it}"
            if it["theme_id"] not in VALIDATED_THEMES:
                assert it["statut"] == "a_valider", f"PRUDENCE violée (thème non validé): {it}"
                assert it["texte_loi_valide"] is False
            assert it["theme_nom"] and it["theme_nom"] != it["theme_id"]
        pytest.finding_id = items[0]["finding_id"]


    # ---- passerelle Module 2
    def test_convert_finding_to_mesure(self, client, dossier):
        fid = getattr(pytest, "finding_id", None)
        assert fid, "finding missing"
        before = client.get(f"{API}/dossiers/{dossier['id']}").json()
        n_before = len(before.get("module2_mesures") or [])

        r = client.post(f"{API}/dossiers/{dossier['id']}/plan-correction/{fid}/to-mesure")
        assert r.status_code == 200, r.text[:400]
        mesure = r.json()["mesure"]
        assert mesure["id"] and mesure["theme_id"]
        assert mesure["source"] == "analyse"
        assert mesure["statut_mise_en_oeuvre"] == "a_faire"

        after = client.get(f"{API}/dossiers/{dossier['id']}").json()
        mesures = after.get("module2_mesures") or []
        assert len(mesures) == n_before + 1
        assert any(m["id"] == mesure["id"] for m in mesures)

        plan = client.get(f"{API}/dossiers/{dossier['id']}/plan-correction").json()
        conv = [p for p in plan if p["finding_id"] == fid]
        assert conv and conv[0]["converti"] is True

    def test_convert_unknown_finding(self, client, dossier):
        r = client.post(f"{API}/dossiers/{dossier['id']}/plan-correction/nope/to-mesure")
        assert r.status_code == 404


    # ---- courriel
    @pytest.mark.parametrize("module", [1, 2])
    def test_draft(self, client, dossier, module):
        r = client.get(f"{API}/dossiers/{dossier['id']}/courriel", params={"module": module})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["to"] == "", "le destinataire doit rester vide"
        assert dossier["nom_entreprise"] in d["subject"]
        assert dossier["neq"] in d["subject"]
        assert d["body"].startswith("Bonjour")
        assert d["pdf_path"].endswith(f"module{module}")
        assert d["pdf_filename"].endswith(".pdf")

    def test_pdf_export_reachable(self, client, dossier):
        r = client.get(f"{API}/dossiers/{dossier['id']}/export/module1")
        assert r.status_code == 200, r.text[:200]
        assert r.content[:4] == b"%PDF"


    # ---- journal d'audit
    def test_audit_contains_engine_actions(self, client, dossier):
        r = client.get(f"{API}/dossiers/{dossier['id']}/audit")
        assert r.status_code == 200
        rows = r.json()
        actions = " | ".join(x["action"] for x in rows)
        for expected in ("Téléversement d'un document", "Ajout d'une URL à analyser",
                         "Analyse d'un document",
                         "Conversion d'un constat en mesure (Module 2)"):
            assert expected in actions, f"action absente du journal: {expected}"
        for x in rows:
            assert x.get("timestamp") and x.get("checksum")
            assert "_id" not in x


    # ---- isolation
    def test_other_user_cannot_access_documents(self, dossier):
        import uuid as _u
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(f"{API}/auth/register", json={
            "email": f"test_{_u.uuid4().hex[:10]}@example.com", "password": "Test1234!",
            "name": "TEST Other", "account_type": "SOLO"})
        assert r.status_code == 200, r.text[:200]
        s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
        s.cookies.clear()
        assert s.get(f"{API}/dossiers/{dossier['id']}/documents").status_code == 404
        assert s.get(f"{API}/dossiers/{dossier['id']}/plan-correction").status_code == 404
        assert s.get(f"{API}/dossiers/{dossier['id']}/courriel").status_code == 404
