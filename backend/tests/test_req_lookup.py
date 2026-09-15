"""Tests — Pré-remplissage REQ (GET /api/v1/req/lookup) — itération 6."""
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


@pytest.fixture(scope="module")
def creds():
    p = Path("/app/memory/test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)", c)
    pw = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)", c)
    if not e or not pw:
        pytest.skip("no credentials")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="module")
def client(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token")
    assert token, "no access_token in login response"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


NEQ = "1140000999"


class TestReqLookupAuth:
    def test_401_without_token(self):
        r = requests.get(f"{API}/req/lookup", params={"neq": NEQ}, timeout=30)
        assert r.status_code in (401, 403), r.text[:300]

    def test_401_bad_token(self):
        r = requests.get(f"{API}/req/lookup", params={"neq": NEQ},
                         headers={"Authorization": "Bearer bogus.token.value"}, timeout=30)
        assert r.status_code in (401, 403), r.text[:300]

    def test_missing_neq_is_422(self, client):
        r = client.get(f"{API}/req/lookup", timeout=30)
        assert r.status_code == 422

    def test_empty_neq_is_422(self, client):
        r = client.get(f"{API}/req/lookup", params={"neq": ""}, timeout=30)
        assert r.status_code == 422


class TestReqLookupShape:
    def test_full_payload(self, client):
        r = client.get(f"{API}/req/lookup", params={"neq": NEQ}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "_id" not in d
        assert d["neq"] == NEQ
        for k in ["source", "nom_entreprise", "forme_juridique", "statut_immatriculation",
                  "etat", "date_immatriculation", "date_mise_a_jour_etat",
                  "regime_constitution", "adresse_domicile", "ville", "code_postal"]:
            assert isinstance(d[k], str) and d[k], f"{k} empty/not str: {d.get(k)}"
        assert d["statut_immatriculation"] == "Immatriculée"
        assert isinstance(d["autres_noms"], list)

        acts = d["activites_economiques"]
        assert isinstance(acts, list) and len(acts) >= 1
        for a in acts:
            assert re.fullmatch(r"\d{6}", a["code_cae"])
            assert a["description"]

        admins = d["administrateurs"]
        assert isinstance(admins, list) and len(admins) >= 1
        assert admins[0]["fonction"] == "Président"
        for a in admins:
            assert a["nom"] and a["fonction"]

        etabs = d["etablissements"]
        assert isinstance(etabs, list) and len(etabs) >= 1
        assert etabs[0]["principal"] is True
        assert sum(1 for e in etabs if e.get("principal")) == 1
        assert d["nombre_etablissements"] == len(etabs)
        assert isinstance(d["nombre_etablissements"], int)
        assert isinstance(d["nombre_employes_estime"], int) and d["nombre_employes_estime"] > 0
        # dates ISO cohérentes
        assert d["date_mise_a_jour_etat"] > d["date_immatriculation"]

    def test_deterministic_same_neq(self, client):
        a = client.get(f"{API}/req/lookup", params={"neq": NEQ}, timeout=30).json()
        b = client.get(f"{API}/req/lookup", params={"neq": NEQ}, timeout=30).json()
        c = client.get(f"{API}/req/lookup", params={"neq": NEQ}, timeout=30).json()
        assert a == b == c

    def test_different_neq_different_data(self, client):
        others = ["1140000999", "1173456789", "1234567890", "1160000001", "1199999999"]
        names = {}
        for n in others:
            d = client.get(f"{API}/req/lookup", params={"neq": n}, timeout=30).json()
            assert d["neq"] == n
            names[n] = d["nom_entreprise"] + "|" + d["adresse_domicile"]
        assert len(set(names.values())) >= 4, f"not enough variation: {names}"

    def test_neq_is_trimmed(self, client):
        d = client.get(f"{API}/req/lookup", params={"neq": f"  {NEQ}  "}, timeout=30).json()
        assert d["neq"] == NEQ
        ref = client.get(f"{API}/req/lookup", params={"neq": NEQ}, timeout=30).json()
        assert d == ref

    def test_non_numeric_neq_returns_422(self, client):
        r = client.get(f"{API}/req/lookup", params={"neq": "ABC"}, timeout=30)
        assert r.status_code == 422, r.text[:200]


class TestDossierIntegration:
    def test_dossier_with_neq_exists_and_inscription_persists_req_data(self, client):
        r = client.get(f"{API}/dossiers", timeout=30)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and rows
        with_neq = [d for d in rows if d.get("neq")]
        assert with_neq, "no dossier with a NEQ available for auto-fetch testing"
        target = next((d for d in with_neq
                       if d["id"] == "2a62630c-ef53-4938-80d9-9879858ae5fc"), with_neq[0])
        neq = target["neq"]

        req = client.get(f"{API}/req/lookup", params={"neq": neq}, timeout=30).json()
        payload = {
            "inscription_data": {
                "neq": neq,
                "nom_entreprise": req["nom_entreprise"],
                "adresse": req["adresse_domicile"],
                "activites": " ; ".join(a["description"] for a in req["activites_economiques"]),
                "nb_etablissements": req["nombre_etablissements"],
                "nb_employes_quebec": req["nombre_employes_estime"],
                "personne_ressource": req["administrateurs"][0]["nom"],
                "req_data": req,
            }
        }
        p = client.patch(f"{API}/dossiers/{target['id']}/inscription", json=payload, timeout=30)
        assert p.status_code == 200, p.text[:400]
        # GET-verify persistence
        g = client.get(f"{API}/dossiers/{target['id']}", timeout=30)
        assert g.status_code == 200
        saved = g.json()["inscription_data"]
        assert saved["nom_entreprise"] == req["nom_entreprise"]
        assert saved["adresse"] == req["adresse_domicile"]
        assert saved["req_data"]["neq"] == neq
        assert saved["req_data"]["administrateurs"] == req["administrateurs"]
        assert "_id" not in g.json()

    def test_other_user_cannot_read_dossier(self, client):
        r = client.get(f"{API}/dossiers/does-not-exist-xyz", timeout=30)
        assert r.status_code == 404
