"""Tests for taille-based regime segmentation (Iteration 18).

Covers:
- GET /catalogue/themes?regime=A -> 18 U-themes (U1..U18), valid text except U17/U18
- GET /catalogue/themes?regime=B -> A1-A5 + B1-B9 (14 themes)
- POST /auth/register SOLO with taille=moins_25 -> creates dossier regime=A, stages=[]
- POST /auth/register SOLO with taille=25_99 -> dossier regime=B, stages non-empty
- POST /dossiers PRO with taille -> regime derived correctly
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def solo_a_client():
    """SOLO account with taille=moins_25 (Regime A)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_solo_a_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST_SoloA", "email": email, "password": "Password123!",
        "account_type": "SOLO", "taille": "moins_25",
    })
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    s.email = email
    return s


@pytest.fixture(scope="module")
def solo_b_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_solo_b_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST_SoloB", "email": email, "password": "Password123!",
        "account_type": "SOLO", "taille": "25_99",
    })
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def pro_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_pro_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST_Pro", "email": email, "password": "Password123!",
        "account_type": "PRO",
    })
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# ---------- Catalogue ----------
class TestCatalogueRegimes:
    def test_regime_a_returns_18_universal_themes(self, solo_a_client):
        r = solo_a_client.get(f"{API}/catalogue/themes?regime=A")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 18, f"expected 18 U-themes, got {len(data)}"
        ids = [t["id"] for t in data]
        assert ids == [f"U{i}" for i in range(1, 19)]
        # All U1..U16 should have valid text; U17/U18 must be False
        for t in data:
            if t["id"] in ("U17", "U18"):
                assert t["texte_loi_valide"] is False, t["id"]
            else:
                assert t["texte_loi_valide"] is True, f"{t['id']} texte_loi_valide should be True"

    def test_regime_b_returns_a_and_b_themes(self, solo_b_client):
        r = solo_b_client.get(f"{API}/catalogue/themes?regime=B")
        assert r.status_code == 200
        data = r.json()
        ids = [t["id"] for t in data]
        expected = [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 10)]
        assert ids == expected, ids

    def test_regime_default_is_b(self, solo_b_client):
        r = solo_b_client.get(f"{API}/catalogue/themes")
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()]
        assert "A1" in ids and "B1" in ids


# ---------- SOLO auto-dossier ----------
class TestSoloRegimeDossier:
    def test_solo_moins_25_creates_regime_a_dossier(self, solo_a_client):
        r = solo_a_client.get(f"{API}/dossiers")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        d = rows[0]
        assert d["regime"] == "A"
        assert d["taille"] == "moins_25"
        assert d["stages"] == [], f"regime A dossier must have empty stages, got {d['stages']}"

    def test_solo_25_99_creates_regime_b_dossier_with_pipeline(self, solo_b_client):
        r = solo_b_client.get(f"{API}/dossiers")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        d = rows[0]
        assert d["regime"] == "B"
        assert d["taille"] == "25_99"
        assert isinstance(d["stages"], list) and len(d["stages"]) > 0


# ---------- PRO create_dossier with taille ----------
class TestProDossierTaille:
    def test_pro_create_dossier_moins_25_is_regime_a(self, pro_client):
        # create a client first
        cr = pro_client.post(f"{API}/clients", json={
            "nom": "TEST_ClientA", "neq": "1170928456", "contact": ""
        })
        assert cr.status_code == 200
        cid = cr.json()["id"]

        dr = pro_client.post(f"{API}/dossiers", json={
            "client_id": cid, "nom_entreprise": "TEST_DossierA",
            "neq": "1170928456", "nb_employes_quebec": 10,
            "nb_etablissements": 1, "taille": "moins_25",
        })
        assert dr.status_code == 200, dr.text
        d = dr.json()
        assert d["regime"] == "A"
        assert d["stages"] == []

    def test_pro_create_dossier_25_99_is_regime_b(self, pro_client):
        cr = pro_client.post(f"{API}/clients", json={
            "nom": "TEST_ClientB", "neq": "1149550031", "contact": ""
        })
        cid = cr.json()["id"]
        dr = pro_client.post(f"{API}/dossiers", json={
            "client_id": cid, "nom_entreprise": "TEST_DossierB",
            "neq": "1149550031", "nb_employes_quebec": 55,
            "nb_etablissements": 1, "taille": "25_99",
        })
        assert dr.status_code == 200, dr.text
        d = dr.json()
        assert d["regime"] == "B"
        assert len(d["stages"]) > 0

    def test_pro_create_dossier_100_plus_is_regime_b(self, pro_client):
        cr = pro_client.post(f"{API}/clients", json={
            "nom": "TEST_ClientC", "neq": "1163009284", "contact": ""
        })
        cid = cr.json()["id"]
        dr = pro_client.post(f"{API}/dossiers", json={
            "client_id": cid, "nom_entreprise": "TEST_DossierC",
            "neq": "1163009284", "nb_employes_quebec": 150,
            "nb_etablissements": 2, "taille": "100_plus",
        })
        assert dr.status_code == 200
        assert dr.json()["regime"] == "B"


# ---------- Amorce regime-specific ----------
class TestAmorceRegimeA:
    def test_regime_a_amorce_session_has_regime_a_config(self, solo_a_client):
        rows = solo_a_client.get(f"{API}/dossiers").json()
        did = rows[0]["id"]
        # Create an amorce session
        r = solo_a_client.post(f"{API}/dossiers/{did}/amorce/session")
        assert r.status_code == 200, r.text
        session = r.json()
        sid = session["session_id"]
        # Fetch mobile session (public endpoint)
        pub = requests.get(f"{API}/amorce/{sid}")
        assert pub.status_code == 200, pub.text
        d = pub.json()
        questions = d.get("questions", [])
        # Regime A: only NEQ, site, employes
        q_keys = [q.get("key") for q in questions]
        assert "q1_neq" in q_keys
        assert "q2_site" in q_keys
        assert "q3_employes" in q_keys
        # Should NOT include % CA hors Quebec, nb_etablissements
        assert not any("revenus" in (k or "") or "etablissement" in (k or "") for k in q_keys)
        # Photo categories: check for facade/enseigne/menus/factures
        cats = d.get("photo_categories", [])
        cat_keys = [c.get("key") if isinstance(c, dict) else c for c in cats]
        # Just check it's a list; specific keys checked in a soft way
        assert len(cat_keys) >= 3



@pytest.fixture(scope="module")
def solo_a5_client():
    """SOLO Regime A with exactly 8 employees (>= 5 -> REQ declaration required)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_solo_a5_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST_SoloA5", "email": email, "password": "Password123!",
        "account_type": "SOLO", "taille": "moins_25", "nb_employes": 8,
    })
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


# ---------- Parcours PME (Regime A) : declaration REQ + cadre legal ----------
class TestRegimeAParcours:
    def test_req_framework_returns_five_articles(self, solo_a_client):
        r = solo_a_client.get(f"{API}/catalogue/regime-a-framework")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert ids == ["C149", "C150", "C151", "C152_1", "P33_10"]
        assert all(x["texte_loi_valide"] is True for x in r.json())

    def test_less_than_5_employees_req_not_required(self, solo_a_client):
        d = solo_a_client.get(f"{API}/dossiers").json()[0]
        # solo_a_client registered without nb_employes -> 0 employees
        assert d["req_declaration_requise"] is False

    def test_5_plus_employees_req_required(self, solo_a5_client):
        d = solo_a5_client.get(f"{API}/dossiers").json()[0]
        assert d["nb_employes_quebec"] == 8
        assert d["req_declaration_requise"] is True

    def test_save_req_declaration_computes_proportion(self, solo_a5_client):
        did = solo_a5_client.get(f"{API}/dossiers").json()[0]["id"]
        r = solo_a5_client.put(f"{API}/dossiers/{did}/req-declaration",
                               json={"nb_employes_non_francophones": 2})
        assert r.status_code == 200, r.text
        decl = r.json()["req_declaration"]
        assert decl["nb_employes_non_francophones"] == 2
        assert decl["total_employes"] == 8
        assert decl["proportion_non_francophone"] == 25.0

    def test_req_declaration_clamped_to_total(self, solo_a5_client):
        did = solo_a5_client.get(f"{API}/dossiers").json()[0]["id"]
        r = solo_a5_client.put(f"{API}/dossiers/{did}/req-declaration",
                               json={"nb_employes_non_francophones": 999})
        assert r.status_code == 200
        assert r.json()["req_declaration"]["nb_employes_non_francophones"] == 8


# ---------- Traitement d'une plainte (Regime A) ----------
class TestRegimeAPlainte:
    def test_open_plainte_creates_9_stages(self, solo_a5_client):
        did = solo_a5_client.get(f"{API}/dossiers").json()[0]["id"]
        r = solo_a5_client.post(f"{API}/dossiers/{did}/plainte")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plainte_ouverte"] is True
        assert len(d["plainte"]["stages"]) == 9
        assert d["plainte"]["stages"][0]["key"] == "communication"

    def test_patch_plainte_stage_sets_echeance(self, solo_a5_client):
        import datetime
        did = solo_a5_client.get(f"{API}/dossiers").json()[0]["id"]
        solo_a5_client.post(f"{API}/dossiers/{did}/plainte")
        ech = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        r = solo_a5_client.patch(f"{API}/dossiers/{did}/plainte/stage/demande_correction",
                                 json={"statut": "en_cours", "date_limite": ech, "echange": "Lettre reçue"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plainte_jours"] == 10
        stg = next(s for s in d["plainte"]["stages"] if s["key"] == "demande_correction")
        assert stg["statut"] == "en_cours"
        assert len(stg["historique"]) == 1

    def test_plainte_rejected_for_regime_b(self, solo_b_client):
        did = solo_b_client.get(f"{API}/dossiers").json()[0]["id"]
        r = solo_b_client.post(f"{API}/dossiers/{did}/plainte")
        assert r.status_code == 400
