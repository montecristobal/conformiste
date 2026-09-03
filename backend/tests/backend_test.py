"""CONFORMISTE backend API tests (auth, clients, dossiers, modules, pipeline, audit, PDF export)."""
import os
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
import requests
from dateutil.relativedelta import relativedelta
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


def new_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client(admin_credentials):
    s = new_session()
    r = s.post(f"{API}/auth/login", json=admin_credentials)
    if r.status_code != 200:
        pytest.fail(f"admin login failed {r.status_code}: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    s.cookies.clear()  # force Bearer path
    return s


def register(account_type):
    s = new_session()
    email = f"test_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "Test1234!", "name": "TEST User",
        "account_type": account_type})
    assert r.status_code == 200, f"register failed {r.status_code} {r.text[:300]}"
    body = r.json()
    s.headers.update({"Authorization": f"Bearer {body['access_token']}"})
    s.cookies.clear()
    return s, body, email


# ---------------------------------------------------------------- auth module
class TestAuth:
    def test_admin_login(self, admin_credentials):
        s = new_session()
        r = s.post(f"{API}/auth/login", json=admin_credentials)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert isinstance(d.get("access_token"), str) and len(d["access_token"]) > 20
        assert d["user"]["email"] == admin_credentials["email"].lower()
        assert d["user"]["account_type"] == "PRO"
        # httpOnly cookie set on login
        cookie = [c for c in r.cookies if c.name == "access_token"]
        assert cookie, f"no access_token cookie; headers={r.headers.get('set-cookie')}"
        assert "httponly" in (r.headers.get("set-cookie", "").lower())

    def test_login_wrong_password(self, admin_credentials):
        r = new_session().post(f"{API}/auth/login", json={
            "email": admin_credentials["email"], "password": "wrong-password-x"})
        assert r.status_code == 401, r.text[:200]
        assert "detail" in r.json()

    def test_login_unknown_email(self):
        r = new_session().post(f"{API}/auth/login", json={
            "email": "nobody_xyz@example.com", "password": "whatever1"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_with_bearer(self, admin_client, admin_credentials):
        r = admin_client.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == admin_credentials["email"].lower()

    def test_me_invalid_token(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
        assert r.status_code == 401

    def test_register_solo_and_pro(self):
        s_solo, body_solo, _ = register("SOLO")
        assert body_solo["user"]["account_type"] == "SOLO"
        assert s_solo.get(f"{API}/auth/me").json()["account_type"] == "SOLO"
        _, body_pro, _ = register("PRO")
        assert body_pro["user"]["account_type"] == "PRO"

    def test_register_duplicate_email(self):
        _, _, email = register("SOLO")
        r = new_session().post(f"{API}/auth/register", json={
            "email": email, "password": "Test1234!", "name": "dup", "account_type": "SOLO"})
        assert r.status_code == 400

    def test_register_invalid_account_type(self):
        r = new_session().post(f"{API}/auth/register", json={
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com", "password": "Test1234!",
            "name": "x", "account_type": "ENTERPRISE"})
        assert r.status_code == 400

    def test_register_short_password(self):
        r = new_session().post(f"{API}/auth/register", json={
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com", "password": "123",
            "name": "x", "account_type": "SOLO"})
        assert r.status_code == 422

    def test_bcrypt_hash_format(self):
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import dotenv_values as dv
        env = dv("/app/backend/.env")

        async def check():
            cli = AsyncIOMotorClient(env["MONGO_URL"].strip('"'))
            u = await cli[env["DB_NAME"].strip('"')].users.find_one(
                {"email": env["ADMIN_EMAIL"].strip('"').lower()})
            cli.close()
            return u
        u = asyncio.get_event_loop().run_until_complete(check())
        assert u is not None, "admin user not seeded"
        assert u["password_hash"].startswith("$2b$"), u["password_hash"][:10]

    def test_brute_force_lockout(self, admin_credentials):
        """Playbook: lockout after 5 failed attempts (informational)."""
        s = new_session()
        codes = []
        for _ in range(6):
            codes.append(s.post(f"{API}/auth/login", json={
                "email": "lockout_probe@example.com", "password": "bad"}).status_code)
        assert any(c == 429 for c in codes), f"no lockout/429 after 6 failures: {codes}"

    def test_logout(self, admin_credentials):
        s = new_session()
        s.post(f"{API}/auth/login", json=admin_credentials)
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200 and r.json().get("ok") is True


# ---------------------------------------------------------------- catalogue
class TestCatalogue:
    def test_themes(self, admin_client):
        r = admin_client.get(f"{API}/catalogue/themes")
        assert r.status_code == 200
        themes = r.json()
        a = [t for t in themes if t["niveau"] == "A"]
        b = [t for t in themes if t["niveau"] == "B"]
        assert len(a) == 5, f"expected 5 niveau A, got {len(a)}"
        assert len(b) == 9, f"expected 9 niveau B, got {len(b)}"
        assert {t["id"] for t in a} == {"A1", "A2", "A3", "A4", "A5"}

    def test_stages(self, admin_client):
        r = admin_client.get(f"{API}/catalogue/stages")
        assert r.status_code == 200
        stages = r.json()
        assert len(stages) == 8
        assert [s["ordre"] for s in stages] == list(range(1, 9))

    def test_catalogue_requires_auth(self):
        assert requests.get(f"{API}/catalogue/themes").status_code == 401


# ---------------------------------------------------------------- clients + dossiers CRUD
class TestClientsAndDossiers:
    def test_create_client_and_list(self, admin_client):
        r = admin_client.post(f"{API}/clients", json={
            "nom": "TEST Client Inc", "neq": "1234567890", "contact": "a@b.com"})
        assert r.status_code == 200, r.text[:300]
        c = r.json()
        assert "_id" not in c
        assert c["nom"] == "TEST Client Inc" and c["neq"] == "1234567890"
        lst = admin_client.get(f"{API}/clients")
        assert lst.status_code == 200
        assert any(x["id"] == c["id"] for x in lst.json())
        assert all("_id" not in x for x in lst.json())

    def test_create_dossier_with_client_and_echeance(self, admin_client):
        cl = admin_client.post(f"{API}/clients", json={"nom": "TEST Client 2"}).json()
        att = (date.today() - timedelta(days=10)).isoformat()
        r = admin_client.post(f"{API}/dossiers", json={
            "nom_entreprise": "TEST Entreprise A", "neq": "999", "client_id": cl["id"],
            "nb_employes_quebec": 120, "nb_etablissements": 3,
            "date_attestation_inscription": att})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        expected = (date.fromisoformat(att) + relativedelta(months=3)).isoformat()
        assert d["echeance_module1"] == expected
        assert d["jours_restants_module1"] == (date.fromisoformat(expected) - date.today()).days
        assert d["comite_requis"] is True
        assert d["annexe_ii_requise"] is True
        assert len(d["stages"]) == 8
        assert "_id" not in d
        # GET persistence
        g = admin_client.get(f"{API}/dossiers/{d['id']}")
        assert g.status_code == 200
        assert g.json()["nom_entreprise"] == "TEST Entreprise A"
        assert g.json()["client_id"] == cl["id"]
        # client filter
        f = admin_client.get(f"{API}/dossiers", params={"client_id": cl["id"]})
        assert f.status_code == 200
        ids = [x["id"] for x in f.json()]
        assert ids == [d["id"]], ids

    def test_urgence_levels(self, admin_client):
        cases = [((date.today() - relativedelta(months=3) + timedelta(days=3)).isoformat(), "critical"),
                 ((date.today() - relativedelta(months=3) + timedelta(days=20)).isoformat(), "approaching"),
                 (date.today().isoformat(), "normal")]
        for att, expected in cases:
            d = admin_client.post(f"{API}/dossiers", json={
                "nom_entreprise": f"TEST Urgence {expected}",
                "date_attestation_inscription": att}).json()
            assert d["urgence_module1"] == expected, (att, d["urgence_module1"])

    def test_no_attestation_date(self, admin_client):
        d = admin_client.post(f"{API}/dossiers", json={"nom_entreprise": "TEST Sans date"}).json()
        assert d["echeance_module1"] is None
        assert d["jours_restants_module1"] is None
        assert d["urgence_module1"] == "normal"
        assert d["comite_requis"] is False and d["annexe_ii_requise"] is False

    def test_dashboard_sorting_by_echeance(self, admin_client):
        rows = admin_client.get(f"{API}/dossiers").json()
        js = [r["jours_restants_module1"] for r in rows]
        non_null = [j for j in js if j is not None]
        assert non_null == sorted(non_null), js
        # None values must be last
        first_none = next((i for i, j in enumerate(js) if j is None), len(js))
        assert all(j is None for j in js[first_none:]), js

    def test_isolation_between_users(self, admin_client):
        d = admin_client.post(f"{API}/dossiers", json={"nom_entreprise": "TEST Private"}).json()
        other, _, _ = register("PRO")
        assert other.get(f"{API}/dossiers/{d['id']}").status_code == 404
        assert d["id"] not in [x["id"] for x in other.get(f"{API}/dossiers").json()]
        assert other.patch(f"{API}/dossiers/{d['id']}/module1",
                           json={"module1_data": {"x": 1}, "module1_meta": {}}).status_code == 404
        assert other.get(f"{API}/dossiers/{d['id']}/audit").status_code == 404
        assert other.get(f"{API}/dossiers/{d['id']}/export/module1").status_code == 404
        # client isolation
        assert not [c for c in other.get(f"{API}/clients").json()]

    def test_dossier_404(self, admin_client):
        assert admin_client.get(f"{API}/dossiers/{uuid.uuid4()}").status_code == 404

    def test_dossier_requires_auth(self):
        assert requests.get(f"{API}/dossiers").status_code == 401
        assert requests.post(f"{API}/dossiers", json={"nom_entreprise": "x"}).status_code == 401

    def test_create_dossier_validation(self, admin_client):
        assert admin_client.post(f"{API}/dossiers", json={}).status_code == 422

    def test_patch_dossier_general(self, admin_client):
        d = admin_client.post(f"{API}/dossiers", json={
            "nom_entreprise": "TEST Patch", "nb_employes_quebec": 10}).json()
        r = admin_client.patch(f"{API}/dossiers/{d['id']}", json={
            "nom_entreprise": "TEST Patch Modifie", "nb_employes_quebec": 150,
            "nb_etablissements": 2})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["comite_requis"] is True
        g = admin_client.get(f"{API}/dossiers/{d['id']}").json()
        assert g["nom_entreprise"] == "TEST Patch Modifie"
        assert g["nb_employes_quebec"] == 150
        assert g["annexe_ii_requise"] is True


# ---------------------------------------------------------------- modules, pipeline, audit, PDF
class TestModulesPipelineAuditExport:
    @pytest.fixture(scope="class")
    def dossier(self, admin_client):
        att = (date.today() - timedelta(days=30)).isoformat()
        d = admin_client.post(f"{API}/dossiers", json={
            "nom_entreprise": "TEST Modules Inc", "neq": "5550001",
            "nb_employes_quebec": 105, "nb_etablissements": 4,
            "date_attestation_inscription": att}).json()
        return d

    def test_module1_save_and_persist(self, admin_client, dossier):
        payload = {"module1_data": {"s1.nom_entreprise": "TEST Modules Inc",
                                    "s4.employes_quebec": 105,
                                    "s4.etablissements": 4,
                                    "s5.politique_linguistique": "oui",
                                    "s5.politique_linguistique_precisez": "Politique 2024"},
                   "module1_meta": {"annexe_i": True, "annexe_ii": True}}
        r = admin_client.patch(f"{API}/dossiers/{dossier['id']}/module1", json=payload)
        assert r.status_code == 200, r.text[:300]
        g = admin_client.get(f"{API}/dossiers/{dossier['id']}").json()
        assert g["module1_data"]["s4.employes_quebec"] == 105
        assert g["module1_data"]["s5.politique_linguistique_precisez"] == "Politique 2024"
        assert g["module1_meta"]["annexe_ii"] is True

    def test_module2_save_and_persist(self, admin_client, dossier):
        mesures = [
            {"id": "m1", "theme_id": "A1", "description": "TEST mesure A1",
             "echeance": "2026-12-31", "statut": "en_cours"},
            {"id": "m2", "theme_id": "B3", "description": "TEST mesure B3",
             "echeance": "2027-01-31", "statut": "a_faire"},
        ]
        r = admin_client.patch(f"{API}/dossiers/{dossier['id']}/module2", json={
            "module2_admin": {"responsable": "TEST Resp"}, "module2_mesures": mesures})
        assert r.status_code == 200, r.text[:300]
        g = admin_client.get(f"{API}/dossiers/{dossier['id']}").json()
        assert len(g["module2_mesures"]) == 2
        assert g["module2_mesures"][0]["theme_id"] == "A1"
        assert g["module2_admin"]["responsable"] == "TEST Resp"
        # delete one measure
        admin_client.patch(f"{API}/dossiers/{dossier['id']}/module2", json={
            "module2_admin": {"responsable": "TEST Resp"}, "module2_mesures": mesures[:1]})
        g2 = admin_client.get(f"{API}/dossiers/{dossier['id']}").json()
        assert len(g2["module2_mesures"]) == 1

    def test_stage_update_and_exchange(self, admin_client, dossier):
        stages = admin_client.get(f"{API}/dossiers/{dossier['id']}").json()["stages"]
        key = stages[2]["key"]
        r = admin_client.patch(f"{API}/dossiers/{dossier['id']}/stage/{key}", json={
            "statut": "en_cours", "date_limite": "2026-09-30",
            "note": "TEST note etape", "echange": "TEST echange OQLF"})
        assert r.status_code == 200, r.text[:300]
        g = admin_client.get(f"{API}/dossiers/{dossier['id']}").json()
        s = next(x for x in g["stages"] if x["key"] == key)
        assert s["statut"] == "en_cours"
        assert s["date_limite"] == "2026-09-30"
        assert s["note"] == "TEST note etape"
        assert len(s["historique"]) == 1
        assert s["historique"][0]["texte"] == "TEST echange OQLF"
        assert s["historique"][0]["auteur"]
        # second exchange appends
        admin_client.patch(f"{API}/dossiers/{dossier['id']}/stage/{key}",
                           json={"echange": "TEST echange 2", "statut": "soumis"})
        s2 = next(x for x in admin_client.get(f"{API}/dossiers/{dossier['id']}").json()["stages"]
                  if x["key"] == key)
        assert len(s2["historique"]) == 2 and s2["statut"] == "soumis"

    def test_stage_unknown_key(self, admin_client, dossier):
        r = admin_client.patch(f"{API}/dossiers/{dossier['id']}/stage/inexistante",
                               json={"statut": "en_cours"})
        assert r.status_code == 404

    def test_export_module1_pdf(self, admin_client, dossier):
        r = admin_client.get(f"{API}/dossiers/{dossier['id']}/export/module1")
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF" and len(r.content) > 1000

    def test_export_module2_pdf(self, admin_client, dossier):
        r = admin_client.get(f"{API}/dossiers/{dossier['id']}/export/module2")
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF" and len(r.content) > 1000

    def test_audit_trail(self, admin_client, dossier):
        rows = admin_client.get(f"{API}/dossiers/{dossier['id']}/audit").json()
        assert isinstance(rows, list) and len(rows) >= 5, len(rows)
        assert all("_id" not in r for r in rows)
        actions = " | ".join(r["action"] for r in rows)
        for expected in ["Création du dossier", "Module 1", "Module 2", "Export PDF", "étape"]:
            assert expected in actions, f"missing audit action {expected}: {actions}"
        ts = [r["timestamp"] for r in rows]
        assert ts == sorted(ts, reverse=True), "audit not sorted desc"
        assert all(r["checksum"] and r["actor_email"] for r in rows)
