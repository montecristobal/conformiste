"""Réinitialise inscription_data du dossier cible pour tester l'auto-fetch REQ (UI)."""
import os, re, requests
from pathlib import Path
from dotenv import dotenv_values

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
c = Path("/app/memory/test_credentials.md").read_text()
email = re.search(r"(?im)^\s*-?\s*Email\s*:\s*(\S+)", c).group(1)
pw = re.search(r"(?im)^\s*-?\s*Password\s*:\s*(\S+)", c).group(1)
s = requests.Session()
r = s.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": pw}, timeout=30)
s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
DID = "2a62630c-ef53-4938-80d9-9879858ae5fc"
d = s.get(f"{BASE}/api/v1/dossiers/{DID}", timeout=30).json()
print("dossier neq:", d.get("neq"), "| titre:", d.get("nom") or d.get("titre"))
p = s.patch(f"{BASE}/api/v1/dossiers/{DID}/inscription", json={"inscription_data": {"neq": d.get("neq")}}, timeout=30)
print("reset status:", p.status_code)
print("after:", s.get(f"{BASE}/api/v1/dossiers/{DID}", timeout=30).json().get("inscription_data"))
