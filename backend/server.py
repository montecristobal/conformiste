from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import re
import uuid
import base64
import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict

import jwt
import bcrypt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Header, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel, EmailStr, Field
from dateutil.relativedelta import relativedelta

from catalogue import THEMES_LEGAUX, PIPELINE_STAGES, UNIVERSAL_THEMES, themes_for_regime, REGIME_A_LEGAL_FRAMEWORK
from req_lookup import simulate_req
from pdf_export import build_module1_pdf, build_module2_pdf
from storage import put_object, get_object, init_storage, APP_NAME, MIME_TYPES
import analysis
import mailer
import amorce
import diagnostic

# ---------------------------------------------------------------- DB / app
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="CONFORMISTE API")
api = APIRouter(prefix="/api/v1")

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("conformiste")


# ---------------------------------------------------------------- auth utils
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Jeton invalide")


# ---------------------------------------------------------------- models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    account_type: str  # PRO | SOLO
    taille: Optional[str] = None  # moins_25 | 25_99 | 100_plus
    nb_employes: Optional[int] = None  # nombre exact d'employés au Québec (Régime A)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ClientIn(BaseModel):
    nom: str
    neq: Optional[str] = ""
    contact: Optional[str] = ""


class DossierIn(BaseModel):
    nom_entreprise: str
    neq: Optional[str] = ""
    client_id: Optional[str] = None
    nb_employes_quebec: Optional[int] = 0
    nb_etablissements: Optional[int] = 1
    taille: Optional[str] = None  # moins_25 | 25_99 | 100_plus
    date_attestation_inscription: Optional[str] = None  # ISO date


class ParcoursAProfilIn(BaseModel):
    neq: Optional[str] = ""
    nom_legal: Optional[str] = ""
    marques: Optional[List[str]] = None
    syndicat: bool = False
    vend_produits: bool = False
    vend_jouets: bool = False
    immo_residentiel: bool = False
    nb_employes: Optional[int] = None
    nb_francais: Optional[int] = None


class U6In(BaseModel):
    postes: List[Dict[str, Any]] = []


class U6MotifIn(BaseModel):
    poste: Dict[str, Any] = {}


class Module1In(BaseModel):
    module1_data: Dict[str, Any] = {}
    module1_meta: Dict[str, Any] = {}


class InscriptionIn(BaseModel):
    inscription_data: Dict[str, Any] = {}


class OqlfIn(BaseModel):
    oqlf_data: Dict[str, Any] = {}


class EnrichIn(BaseModel):
    site_url: Optional[str] = None


class LangProofIn(BaseModel):
    site_url: Optional[str] = None
    social_urls: Optional[List[str]] = None


class Module2In(BaseModel):
    module2_admin: Dict[str, Any] = {}
    module2_mesures: List[Dict[str, Any]] = []


VALID_STATUTS = {"a_faire", "en_cours", "soumis", "accepte", "refuse"}


class StageUpdateIn(BaseModel):
    statut: Optional[str] = None
    date_limite: Optional[str] = None
    date_soumission: Optional[str] = None
    note: Optional[str] = None
    echange: Optional[str] = None  # nouvel échange OQLF à ajouter à l'historique


# ---------------------------------------------------------------- helpers
def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True,
                        samesite="none", max_age=604800, path="/")


def new_dossier_stages() -> List[dict]:
    return [{"key": s["key"], "ordre": s["ordre"], "label": s["label"],
             "description": s["description"], "module": s.get("module"),
             "statut": "a_faire", "date_limite": None, "date_soumission": None,
             "note": "", "historique": []} for s in PIPELINE_STAGES]


PLAINTE_STAGES = [
    {"key": "communication", "ordre": 1, "label": "Communication initiale de l'OQLF",
     "description": "Visite d'un inspecteur ou lettre de l'Office. Un inspecteur doit, sur demande, attester sa qualité et présenter sa carte d'identité — exigez-la. Tout refus de collaborer est une entrave, passible automatiquement d'une amende. Un inspecteur n'est pas un conseiller en francisation."},
    {"key": "analyse", "ordre": 2, "label": "Analyse de la plainte par l'Office",
     "description": "L'Office analyse le dossier pour déterminer si la plainte est fondée."},
    {"key": "demande_correction", "ordre": 3, "label": "Demande de correction",
     "description": "Si la plainte est fondée, l'OQLF informe l'entreprise par lettre et demande des corrections selon un échéancier proposé."},
    {"key": "negociation", "ordre": 4, "label": "Négociation de l'échéancier",
     "description": "L'entreprise peut modifier l'échéancier en invoquant ses raisons et négocier un correctif acceptable ainsi qu'une date d'échéance."},
    {"key": "preavis", "ordre": 5, "label": "Pré-avis d'ordonnance",
     "description": "Si l'entreprise ne donne pas suite, l'Office émet un pré-avis d'ordonnance de se conformer à la loi."},
    {"key": "ordonnance", "ordre": 6, "label": "Ordonnance",
     "description": "15 jours après le pré-avis, l'ordonnance est émise si rien n'a été corrigé."},
    {"key": "contestation", "ordre": 7, "label": "Contestation au Tribunal administratif du Québec",
     "description": "L'entreprise a 30 jours pour contester l'ordonnance devant le TAQ, qui peut seulement la confirmer ou l'infirmer. Si elle est infirmée, la plainte peut être fermée ou reformulée."},
    {"key": "execution", "ordre": 8, "label": "Exécution ou référé au Procureur général",
     "description": "Si l'ordonnance est confirmée, l'entreprise doit s'exécuter dans les délais impartis ; à défaut, le dossier est référé au Procureur général, qui peut intenter une poursuite (amende par jugement)."},
    {"key": "resolution", "ordre": 9, "label": "Résolution",
     "description": "Clôture du dossier : résolu à l'amiable, classé, ordonnance infirmée, ou amende."},
]

VALID_PLAINTE_STATUTS = {"a_faire", "en_cours", "fait", "sans_objet"}


def new_plainte() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {"id": str(uuid.uuid4()), "ouverte": True, "reference_oqlf": "",
            "type_communication": None, "resolution": None,
            "stages": [{"key": s["key"], "ordre": s["ordre"], "label": s["label"],
                        "description": s["description"], "statut": "a_faire",
                        "date": None, "date_limite": None, "note": "", "historique": []}
                       for s in PLAINTE_STAGES],
            "created_at": now, "updated_at": now}


def _plainte_next_echeance(pl: Optional[dict]):
    if not pl or not pl.get("ouverte"):
        return None, None
    today = datetime.now(timezone.utc).date()
    best = None
    for s in pl.get("stages", []):
        if s.get("statut") in ("fait", "sans_objet") or not s.get("date_limite"):
            continue
        try:
            j = (datetime.fromisoformat(s["date_limite"]).date() - today).days
        except Exception:
            continue
        if best is None or j < best[1]:
            best = (s["date_limite"], j)
    return (best[0], best[1]) if best else (None, None)


def urgence_for(days: Optional[int]) -> str:
    if days is None:
        return "normal"
    if days <= 7:
        return "critical"
    if days <= 30:
        return "approaching"
    return "normal"


def regime_from(taille: Optional[str], nb_employes: Optional[int] = None) -> str:
    """Régime A (< 25 employés, obligations universelles) vs Régime B (25+, francisation)."""
    if taille == "moins_25":
        return "A"
    if taille in ("25_99", "100_plus"):
        return "B"
    if nb_employes is not None and nb_employes < 25:
        return "A"
    return "B"


def _parcours_a_gate_ok(gate: Optional[str], profil: dict) -> bool:
    if gate == "syndicat":
        return bool(profil.get("syndicat"))
    if gate == "produits":
        return bool(profil.get("vend_produits"))
    if gate == "jouets":
        return bool(profil.get("vend_jouets"))
    if gate == "immo":
        return bool(profil.get("immo_residentiel"))
    return True


def parcours_a_sets(dossier: dict):
    """Retourne (applicable, info_only) : codes d'obligations universelles à évaluer
    vs. à afficher en simple rappel (protections après les faits U4/U5)."""
    profil = dossier.get("parcours_a_profil") or {}
    completed = bool(profil.get("completed"))
    applicable, info_only = [], []
    for t in UNIVERSAL_THEMES:
        g = t.get("gate")
        if g == "info_only":
            info_only.append(t["id"])
            continue
        if not completed or _parcours_a_gate_ok(g, profil):
            applicable.append(t["id"])
    return applicable, info_only


def enrich_dossier(d: dict) -> dict:
    d.pop("_id", None)
    d["regime"] = d.get("regime") or "B"
    ech = None
    if d.get("date_attestation_inscription"):
        try:
            base = datetime.fromisoformat(d["date_attestation_inscription"]).date()
            ech = (base + relativedelta(months=3)).isoformat()
        except Exception:
            ech = None
    d["echeance_module1"] = ech
    jours = None
    if ech:
        jours = (datetime.fromisoformat(ech).date() - datetime.now(timezone.utc).date()).days
    d["jours_restants_module1"] = jours
    d["urgence_module1"] = urgence_for(jours)
    d["comite_requis"] = (d.get("nb_employes_quebec") or 0) >= 100
    d["annexe_ii_requise"] = (d.get("nb_etablissements") or 1) > 1
    d["req_declaration_requise"] = d.get("regime") == "A" and (d.get("nb_employes_quebec") or 0) >= 5
    d.setdefault("req_declaration", None)
    _ua = d.get("parcours_a_elements") or {}
    _applicable, _info_only = parcours_a_sets(d)
    d["parcours_a_applicable"] = _applicable
    d["parcours_a_info_only"] = _info_only
    d["parcours_a_profil"] = d.get("parcours_a_profil") or None
    _traites = sum(1 for c in _applicable if (_ua.get(c) or {}).get("statut") not in (None, "non_evalue"))
    if d["req_declaration_requise"] and d.get("req_declaration"):
        _traites += 1
    d["parcours_a_total"] = len(_applicable) + (1 if d["req_declaration_requise"] else 0)
    d["parcours_a_traites"] = _traites
    pl = d.get("plainte")
    d["plainte_ouverte"] = bool(pl and pl.get("ouverte"))
    pe, pj = _plainte_next_echeance(pl)
    d["plainte_echeance"] = pe
    d["plainte_jours"] = pj
    d["plainte_urgence"] = urgence_for(pj)
    return d


async def audit(dossier_id: str, actor: dict, action: str, details: str = ""):
    ts = datetime.now(timezone.utc).isoformat()
    payload = f"{dossier_id}|{ts}|{actor.get('email')}|{action}|{details}"
    entry = {
        "id": str(uuid.uuid4()),
        "dossier_id": dossier_id,
        "timestamp": ts,
        "actor_email": actor.get("email"),
        "mode": actor.get("account_type"),
        "action": action,
        "details": details,
        "checksum": hashlib.sha256(payload.encode()).hexdigest()[:16],
    }
    await db.audit_logs.insert_one(entry)


async def get_owned_dossier(dossier_id: str, user: dict) -> dict:
    d = await db.dossiers.find_one({"id": dossier_id, "owner_id": user["id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return d


# ---------------------------------------------------------------- auth routes
@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if body.account_type not in ("PRO", "SOLO"):
        raise HTTPException(status_code=400, detail="Type de compte invalide")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Cette adresse courriel est déjà utilisée")
    doc = {"email": email, "password_hash": hash_password(body.password),
           "name": body.name, "account_type": body.account_type, "role": "user",
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    if body.account_type == "SOLO":
        regime = regime_from(body.taille)
        ddoc = {
            "id": str(uuid.uuid4()), "owner_id": uid, "client_id": None,
            "nom_entreprise": body.name, "neq": "",
            "nb_employes_quebec": body.nb_employes or 0, "nb_etablissements": 1,
            "regime": regime, "taille": body.taille,
            "date_attestation_inscription": None,
            "stages": [] if regime == "A" else new_dossier_stages(),
            "module1_data": {}, "module1_meta": {},
            "module2_admin": {}, "module2_mesures": [], "inscription_data": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.dossiers.insert_one(dict(ddoc))
    token = create_access_token(uid, email)
    set_auth_cookie(response, token)
    return {"access_token": token,
            "user": {"id": uid, "email": email, "name": body.name,
                     "account_type": body.account_type}}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    identifier = email
    rec = await db.login_attempts.find_one({"identifier": identifier})
    now = datetime.now(timezone.utc)
    if rec and rec.get("locked_until"):
        locked_until = datetime.fromisoformat(rec["locked_until"])
        if locked_until > now:
            raise HTTPException(status_code=429,
                                detail="Trop de tentatives. Réessayez dans quelques minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        attempts = (rec.get("attempts", 0) if rec else 0) + 1
        upd = {"identifier": identifier, "attempts": attempts,
               "updated_at": now.isoformat()}
        if attempts >= 5:
            upd["locked_until"] = (now + timedelta(minutes=15)).isoformat()
            upd["attempts"] = 0
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": upd}, upsert=True)
        raise HTTPException(status_code=401, detail="Courriel ou mot de passe incorrect")
    await db.login_attempts.delete_one({"identifier": identifier})
    uid = str(user["_id"])
    token = create_access_token(uid, email)
    set_auth_cookie(response, token)
    return {"access_token": token,
            "user": {"id": uid, "email": email, "name": user.get("name"),
                     "account_type": user.get("account_type")}}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name"),
            "account_type": user.get("account_type")}


# ---------------------------------------------------------------- catalogue
@api.get("/catalogue/themes")
async def get_themes(regime: Optional[str] = None, user: dict = Depends(get_current_user)):
    return themes_for_regime(regime)


@api.get("/catalogue/stages")
async def get_stages(user: dict = Depends(get_current_user)):
    return PIPELINE_STAGES


@api.get("/req/lookup")
async def req_lookup(neq: str = Query(..., min_length=1),
                     user: dict = Depends(get_current_user)):
    neq = neq.strip()
    if not re.fullmatch(r"\d{9,10}", neq):
        raise HTTPException(status_code=422, detail="NEQ invalide : 9 ou 10 chiffres attendus.")
    return simulate_req(neq)


# ---------------------------------------------------------------- clients (PRO)
@api.get("/clients")
async def list_clients(user: dict = Depends(get_current_user)):
    rows = await db.clients.find({"owner_id": user["id"]}, {"_id": 0}).to_list(1000)
    return rows


@api.post("/clients")
async def create_client(body: ClientIn, user: dict = Depends(get_current_user)):
    doc = {"id": str(uuid.uuid4()), "owner_id": user["id"], "nom": body.nom,
           "neq": body.neq, "contact": body.contact,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.clients.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


# ---------------------------------------------------------------- dossiers
@api.get("/dossiers")
async def list_dossiers(client_id: Optional[str] = None,
                        user: dict = Depends(get_current_user)):
    q: Dict[str, Any] = {"owner_id": user["id"]}
    if client_id:
        q["client_id"] = client_id
    rows = await db.dossiers.find(q).to_list(1000)
    rows = [enrich_dossier(r) for r in rows]
    rows.sort(key=lambda r: (r["jours_restants_module1"] is None,
                             r["jours_restants_module1"] if r["jours_restants_module1"] is not None else 0))
    return rows


@api.post("/dossiers")
async def create_dossier(body: DossierIn, user: dict = Depends(get_current_user)):
    regime = regime_from(body.taille, body.nb_employes_quebec)
    doc = {
        "id": str(uuid.uuid4()), "owner_id": user["id"], "client_id": body.client_id,
        "nom_entreprise": body.nom_entreprise, "neq": body.neq,
        "nb_employes_quebec": body.nb_employes_quebec,
        "nb_etablissements": body.nb_etablissements,
        "regime": regime, "taille": body.taille,
        "date_attestation_inscription": body.date_attestation_inscription,
        "stages": [] if regime == "A" else new_dossier_stages(),
        "module1_data": {}, "module1_meta": {},
        "module2_admin": {}, "module2_mesures": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.dossiers.insert_one(dict(doc))
    await audit(doc["id"], user, "Création du dossier", doc["nom_entreprise"])
    return enrich_dossier(doc)


@api.get("/dossiers/{dossier_id}")
async def get_dossier(dossier_id: str, user: dict = Depends(get_current_user)):
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}")
async def update_dossier(dossier_id: str, body: DossierIn,
                         user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    upd = body.model_dump(exclude_none=True)
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user, "Mise à jour des informations générales")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/module1")
async def save_module1(dossier_id: str, body: Module1In,
                       user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    upd = {"module1_data": body.module1_data, "module1_meta": body.module1_meta,
           "updated_at": datetime.now(timezone.utc).isoformat()}
    # source de vérité : synchroniser le nombre d'employés / établissements depuis la section 4
    emp = body.module1_data.get("s4.employes_quebec")
    etab = body.module1_data.get("s4.etablissements")
    if isinstance(emp, (int, float)):
        upd["nb_employes_quebec"] = int(emp)
    if isinstance(etab, (int, float)):
        upd["nb_etablissements"] = int(etab)
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user, "Enregistrement du Module 1 (Analyse linguistique)")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/module2")
async def save_module2(dossier_id: str, body: Module2In,
                       user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    EXTERNAL_FIELDS = ("external_legal_object_id", "external_source_type", "external_version_id",
                       "external_citation", "reference_date", "retrieved_at")
    for m in body.module2_mesures:
        for f in EXTERNAL_FIELDS:
            m.setdefault(f, None)
    await db.dossiers.update_one({"id": dossier_id}, {"$set": {
        "module2_admin": body.module2_admin, "module2_mesures": body.module2_mesures,
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit(dossier_id, user, "Enregistrement du Module 2 (Programme de francisation)")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/inscription")
async def save_inscription(dossier_id: str, body: InscriptionIn,
                           user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    upd = {"inscription_data": body.inscription_data,
           "updated_at": datetime.now(timezone.utc).isoformat()}
    emp = body.inscription_data.get("nb_employes_quebec")
    etab = body.inscription_data.get("nb_etablissements")
    if isinstance(emp, (int, float)):
        upd["nb_employes_quebec"] = int(emp)
    if isinstance(etab, (int, float)):
        upd["nb_etablissements"] = int(etab)
    neq = body.inscription_data.get("neq")
    if isinstance(neq, str) and neq:
        upd["neq"] = neq
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user, "Entrevue d'inscription enregistrée")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/oqlf")
async def save_oqlf(dossier_id: str, body: OqlfIn,
                    user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    upd = {"oqlf_data": body.oqlf_data,
           "updated_at": datetime.now(timezone.utc).isoformat()}
    emp = body.oqlf_data.get("nb_employes_actuel")
    etab = body.oqlf_data.get("nb_etablissements")
    if isinstance(emp, (int, float)):
        upd["nb_employes_quebec"] = int(emp)
    if isinstance(etab, (int, float)):
        upd["nb_etablissements"] = int(etab)
    neq = body.oqlf_data.get("neq")
    if isinstance(neq, str) and neq:
        upd["neq"] = neq
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user, "Formulaire d'inscription OQLF enregistré")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.get("/dossiers/{dossier_id}/export/oqlf")
async def export_oqlf(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    await audit(dossier_id, user, "Export PDF — Formulaire d'inscription OQLF")
    from pdf_export import build_oqlf_pdf
    buf = build_oqlf_pdf(d)
    fn = f"formulaire_inscription_oqlf_{d.get('neq') or dossier_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.post("/dossiers/{dossier_id}/module1/enrich")
async def module1_enrich(dossier_id: str, body: EnrichIn,
                         user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    from enrichment import enrich_module1
    oqlf = d.get("oqlf_data", {}) or {}
    m1 = d.get("module1_data", {}) or {}
    site = (body.site_url or "").strip() or m1.get("s1.sites_web") or oqlf.get("site_web") or ""
    nom = d.get("nom_entreprise") or oqlf.get("nom_entreprise") or m1.get("s1.nom") or ""
    neq = d.get("neq") or oqlf.get("neq") or ""
    result = await enrich_module1(nom, neq, site)
    await audit(dossier_id, user, "Pré-remplissage par recherche Web (analyse linguistique)")
    return result


def _reseau_name(url: str):
    u = (url or "").lower()
    for dom, nm in (("linkedin", "LinkedIn"), ("facebook", "Facebook"),
                    ("instagram", "Instagram"), ("x.com", "X"), ("twitter", "X (Twitter)"),
                    ("youtube", "YouTube")):
        if dom in u:
            return nm
    return None


@api.post("/dossiers/{dossier_id}/language-proof")
async def language_proof(dossier_id: str, body: LangProofIn,
                         user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    from enrichment import detect_language, discover_social_urls
    from screenshot import capture_screenshot, stamp_proof
    from analysis import fetch_url_text as _fetch, UrlValidationError as _UVE
    oqlf = d.get("oqlf_data", {}) or {}
    m1 = d.get("module1_data", {}) or {}
    site = (body.site_url or "").strip() or m1.get("s1.sites_web") or oqlf.get("site_web") or ""
    nom = d.get("nom_entreprise") or oqlf.get("nom_entreprise") or m1.get("s1.nom") or ""

    targets = []
    if site:
        targets.append(("site", site))
    socials = body.social_urls or await run_in_threadpool(discover_social_urls, nom, 2)
    for su in (socials or [])[:2]:
        targets.append(("social", su))

    evidence, warnings = [], []
    for kind, url in targets[:3]:
        lang = {"lang": "inconnu", "confidence": None, "is_french": None}
        try:
            text = await run_in_threadpool(_fetch, url)
            lang = detect_language(text)
        except _UVE:
            warnings.append(f"URL refusée : {url}")
            continue
        except Exception:
            warnings.append(f"Contenu inaccessible : {url}")
        doc_id = None
        try:
            png = await run_in_threadpool(capture_screenshot, url)
            if lang.get("is_french") is None:
                lang_label = "indéterminée"
            else:
                cf = f" ({int(lang['confidence'] * 100)}%)" if lang.get("confidence") else ""
                lang_label = f"{'français' if lang['is_french'] else 'autre langue'} — {lang['lang']}{cf}"
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            stamp_lines = [
                "PREUVE CONFORMISTE — Analyse de la situation linguistique (Charte de la langue française)",
                f"URL : {url}",
                f"Langue détectée : {lang_label}    |    Capture horodatée : {ts}",
            ]
            png = await run_in_threadpool(stamp_proof, png, stamp_lines)
            path = f"{APP_NAME}/preuves/{user['id']}/{uuid.uuid4()}.png"
            res = await run_in_threadpool(put_object, path, png, "image/png")
            doc = {
                "id": str(uuid.uuid4()), "dossier_id": dossier_id, "type": "file", "kind": "image",
                "original_filename": f"Preuve linguistique — {url}", "storage_path": res["path"],
                "content_type": "image/png", "size": res.get("size", len(png)), "url": url,
                "source": "preuve-langue", "analysis": None, "is_deleted": False,
                "ev_kind": kind, "lang": lang.get("lang"), "is_french": lang.get("is_french"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.documents.insert_one(dict(doc))
            doc_id = doc["id"]
        except Exception:
            warnings.append(f"Capture d'écran impossible : {url}")
        evidence.append({"kind": kind, "url": url, "lang": lang["lang"],
                         "confidence": lang["confidence"], "is_french": lang["is_french"],
                         "document_id": doc_id})

    proposals = []
    site_ev = next((e for e in evidence if e["kind"] == "site"), None)
    if site_ev and site_ev["is_french"] is not None:
        proposals.append({
            "key": "s8.e_site_web", "label": "Le(s) site(s) Web sont en français (8.14)",
            "value": "Oui" if site_ev["is_french"] else "Non", "source": "détection de langue",
            "confidence": site_ev["confidence"], "note": f"Langue détectée : {site_ev['lang']}"})
    soc = [e for e in evidence if e["kind"] == "social"]
    soc_valid = [e for e in soc if e["is_french"] is not None]
    if soc_valid:
        proposals.append({
            "key": "s8.medias_sociaux",
            "label": "Contenus publicitaires sur médias sociaux en français (8.15)",
            "value": "Oui" if any(e["is_french"] for e in soc_valid) else "Non",
            "source": "détection de langue", "confidence": None,
            "note": "D'après les pages de médias sociaux détectées"})
    reseaux = []
    for e in soc:
        nm = _reseau_name(e["url"])
        if nm and nm not in reseaux:
            reseaux.append(nm)
    if reseaux:
        proposals.append({
            "key": "s8.medias_sociaux_reseaux", "label": "Principaux médias sociaux utilisés",
            "value": ", ".join(reseaux), "source": "recherche Web", "confidence": None,
            "note": "Réseaux découverts en ligne"})

    await audit(dossier_id, user, "Évaluation de la langue + preuve (capture d'écran)")
    return {"proposals": proposals, "evidence": evidence, "warnings": warnings}


@api.get("/dossiers/{dossier_id}/export/inscription")
async def export_inscription(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    await audit(dossier_id, user, "Export PDF — Document d'inscription")
    from pdf_export import build_inscription_pdf
    buf = build_inscription_pdf(d)
    fn = f"inscription_{d.get('neq') or dossier_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.patch("/dossiers/{dossier_id}/stage/{stage_key}")
async def update_stage(dossier_id: str, stage_key: str, body: StageUpdateIn,
                       user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if body.statut is not None and body.statut not in VALID_STATUTS:
        raise HTTPException(status_code=400, detail="Statut invalide")
    stages = d.get("stages", [])
    found = None
    for s in stages:
        if s["key"] == stage_key:
            found = s
            if body.statut is not None:
                s["statut"] = body.statut
            if body.date_limite is not None:
                s["date_limite"] = body.date_limite
            if body.date_soumission is not None:
                s["date_soumission"] = body.date_soumission
            if body.note is not None:
                s["note"] = body.note
            if body.echange:
                s.setdefault("historique", []).append({
                    "date": datetime.now(timezone.utc).isoformat(),
                    "texte": body.echange, "auteur": user["email"]})
            break
    if not found:
        raise HTTPException(status_code=404, detail="Étape introuvable")
    await db.dossiers.update_one({"id": dossier_id}, {"$set": {
        "stages": stages, "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit(dossier_id, user, f"Mise à jour de l'étape « {found['label']} »",
                body.statut or "")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.get("/dossiers/{dossier_id}/audit")
async def dossier_audit(dossier_id: str, user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    rows = await db.audit_logs.find({"dossier_id": dossier_id}, {"_id": 0}).to_list(2000)
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    return rows


@api.get("/dossiers/{dossier_id}/export/module1")
async def export_module1(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    await audit(dossier_id, user, "Export PDF — Module 1 (Analyse linguistique)")
    proof_images = []
    docs = await db.documents.find(
        {"dossier_id": dossier_id, "source": "preuve-langue", "is_deleted": {"$ne": True}}
    ).sort("created_at", 1).to_list(50)
    for doc in docs:
        try:
            content, _ct = await run_in_threadpool(get_object, doc["storage_path"])
            proof_images.append((doc.get("original_filename", "Preuve linguistique"), content))
        except Exception:
            continue
    buf = build_module1_pdf(d, proof_images=proof_images)
    fn = f"analyse_linguistique_{d.get('neq') or dossier_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.get("/catalogue/regime-a-framework")
async def get_regime_a_framework(user: dict = Depends(get_current_user)):
    return REGIME_A_LEGAL_FRAMEWORK


class ReqDeclarationIn(BaseModel):
    nb_employes_non_francophones: int = 0


class PlainteMetaIn(BaseModel):
    reference_oqlf: Optional[str] = None
    type_communication: Optional[str] = None  # inspection | lettre
    resolution: Optional[str] = None  # amiable | classee | infirmee | amende
    ouverte: Optional[bool] = None


class PlainteStageIn(BaseModel):
    statut: Optional[str] = None
    date: Optional[str] = None
    date_limite: Optional[str] = None
    note: Optional[str] = None
    echange: Optional[str] = None


VALID_ELEMENT_STATUTS = {"non_evalue", "conforme", "a_valider", "non_conforme", "sans_objet"}


class ParcoursAElementIn(BaseModel):
    statut: Optional[str] = None
    note: Optional[str] = None
    date_debut: Optional[str] = None
    date_echeance: Optional[str] = None
    incontournable: Optional[bool] = None
    donnees: Optional[Dict[str, Any]] = None


@api.patch("/dossiers/{dossier_id}/parcours-a/element/{code}")
async def update_parcours_a_element(dossier_id: str, code: str, body: ParcoursAElementIn,
                                    user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if (d.get("regime") or "B") != "A":
        raise HTTPException(status_code=400, detail="Réservé au régime des obligations universelles.")
    if body.statut is not None and body.statut not in VALID_ELEMENT_STATUTS:
        raise HTTPException(status_code=400, detail="Statut invalide")
    els = d.get("parcours_a_elements") or {}
    cur = els.get(code, {})
    if body.statut is not None:
        cur["statut"] = body.statut
    if body.note is not None:
        cur["note"] = body.note
    if body.date_debut is not None:
        cur["date_debut"] = body.date_debut or None
    if body.date_echeance is not None:
        cur["date_echeance"] = body.date_echeance or None
    if body.incontournable is not None:
        cur["incontournable"] = bool(body.incontournable)
    if body.donnees is not None:
        cur["donnees"] = body.donnees
        # L'outil DOCUMENTE, il ne juge pas : dès qu'une donnée est saisie et
        # qu'aucun statut n'est fixé, on marque « à valider » (jamais conforme auto).
        if body.statut is None and cur.get("statut") in (None, "non_evalue") and any(
                v not in (None, "", []) for v in body.donnees.values()):
            cur["statut"] = "a_valider"
    cur["updated_at"] = datetime.now(timezone.utc).isoformat()
    els[code] = cur
    await db.dossiers.update_one({"id": dossier_id},
                                 {"$set": {"parcours_a_elements": els, "updated_at": cur["updated_at"]}})
    await audit(dossier_id, user, f"Parcours A — élément {code}", body.statut or "")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.get("/catalogue/parcours-a/questions")
async def get_parcours_a_questions(user: dict = Depends(get_current_user)):
    from catalogue import PARCOURS_A_QUESTIONS
    return PARCOURS_A_QUESTIONS


class MesureIn(BaseModel):
    parcours: str = "B"  # A (projet) | B (plainte)
    titre: str
    element_code: Optional[str] = None
    no_dossier_oqlf: Optional[str] = ""
    description: Optional[str] = ""
    moyen: Optional[str] = ""
    responsable: Optional[str] = ""
    date_debut: Optional[str] = None
    date_echeance: Optional[str] = None
    incontournable: bool = False
    statut: Optional[str] = "reception"
    validite: Optional[str] = None  # fondee | non_fondee
    gravite: Optional[str] = None   # critique | moyen


class MesurePatchIn(BaseModel):
    titre: Optional[str] = None
    element_code: Optional[str] = None
    no_dossier_oqlf: Optional[str] = None
    description: Optional[str] = None
    moyen: Optional[str] = None
    responsable: Optional[str] = None
    date_debut: Optional[str] = None
    date_echeance: Optional[str] = None
    incontournable: Optional[bool] = None
    statut: Optional[str] = None
    validite: Optional[str] = None
    gravite: Optional[str] = None
    echange: Optional[str] = None
    checklist: Optional[list] = None


@api.post("/dossiers/{dossier_id}/mesures")
async def create_mesure(dossier_id: str, body: MesureIn, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    now = datetime.now(timezone.utc).isoformat()
    m = {"id": str(uuid.uuid4()), "parcours": body.parcours, "titre": body.titre,
         "element_code": body.element_code, "no_dossier_oqlf": body.no_dossier_oqlf or "",
         "description": body.description or "", "moyen": body.moyen or "",
         "responsable": body.responsable or "", "date_debut": body.date_debut,
         "date_echeance": body.date_echeance, "incontournable": bool(body.incontournable),
         "statut": body.statut or "reception", "validite": body.validite, "gravite": body.gravite,
         "checklist": [], "journal": [], "created_at": now, "updated_at": now}
    await db.dossiers.update_one({"id": dossier_id}, {"$push": {"mesures": m}, "$set": {"updated_at": now}})
    await audit(dossier_id, user, f"Mesure créée — {body.titre}")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/mesures/{mesure_id}")
async def update_mesure(dossier_id: str, mesure_id: str, body: MesurePatchIn,
                        user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    mesures = d.get("mesures") or []
    found = None
    for m in mesures:
        if m["id"] == mesure_id:
            found = m
            for f in ("titre", "element_code", "no_dossier_oqlf", "description", "moyen",
                      "responsable", "date_debut", "date_echeance", "incontournable",
                      "statut", "validite", "gravite"):
                v = getattr(body, f)
                if v is not None:
                    m[f] = v
            if body.checklist is not None:
                m["checklist"] = body.checklist
            if body.echange:
                m.setdefault("journal", []).append({
                    "date": datetime.now(timezone.utc).isoformat(),
                    "auteur": user["email"], "texte": body.echange})
            m["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    if not found:
        raise HTTPException(status_code=404, detail="Mesure introuvable")
    await db.dossiers.update_one({"id": dossier_id},
                                 {"$set": {"mesures": mesures, "updated_at": found["updated_at"]}})
    await audit(dossier_id, user, f"Mesure mise à jour — {found.get('titre', '')}", body.statut or "")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.delete("/dossiers/{dossier_id}/mesures/{mesure_id}")
async def delete_mesure(dossier_id: str, mesure_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    mesures = [m for m in (d.get("mesures") or []) if m["id"] != mesure_id]
    await db.dossiers.update_one({"id": dossier_id}, {"$set": {"mesures": mesures}})
    await audit(dossier_id, user, "Mesure supprimée")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.post("/dossiers/{dossier_id}/plainte")
async def open_plainte(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if (d.get("regime") or "B") != "A":
        raise HTTPException(status_code=400,
                            detail="Le traitement d'une plainte est réservé au régime des obligations universelles (< 25 employés).")
    pl = d.get("plainte")
    if not pl:
        pl = new_plainte()
        await db.dossiers.update_one({"id": dossier_id},
                                     {"$set": {"plainte": pl, "updated_at": pl["updated_at"]}})
        await audit(dossier_id, user, "Ouverture d'un dossier de plainte")
    elif not pl.get("ouverte"):
        await db.dossiers.update_one({"id": dossier_id}, {"$set": {"plainte.ouverte": True}})
        await audit(dossier_id, user, "Réouverture du dossier de plainte")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/plainte")
async def update_plainte_meta(dossier_id: str, body: PlainteMetaIn,
                              user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    pl = d.get("plainte")
    if not pl:
        raise HTTPException(status_code=404, detail="Aucun dossier de plainte.")
    upd = {}
    for f in ("reference_oqlf", "type_communication", "resolution", "ouverte"):
        v = getattr(body, f)
        if v is not None:
            upd[f"plainte.{f}"] = v
    ts = datetime.now(timezone.utc).isoformat()
    upd["plainte.updated_at"] = ts
    upd["updated_at"] = ts
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user, "Mise à jour du dossier de plainte")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


@api.patch("/dossiers/{dossier_id}/plainte/stage/{stage_key}")
async def update_plainte_stage(dossier_id: str, stage_key: str, body: PlainteStageIn,
                               user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    pl = d.get("plainte")
    if not pl:
        raise HTTPException(status_code=404, detail="Aucun dossier de plainte.")
    if body.statut is not None and body.statut not in VALID_PLAINTE_STATUTS:
        raise HTTPException(status_code=400, detail="Statut invalide")
    found = None
    for s in pl.get("stages", []):
        if s["key"] == stage_key:
            found = s
            if body.statut is not None:
                s["statut"] = body.statut
            if body.date is not None:
                s["date"] = body.date
            if body.date_limite is not None:
                s["date_limite"] = body.date_limite
            if body.note is not None:
                s["note"] = body.note
            if body.echange:
                s.setdefault("historique", []).append({
                    "date": datetime.now(timezone.utc).isoformat(),
                    "texte": body.echange, "auteur": user["email"]})
            break
    if not found:
        raise HTTPException(status_code=404, detail="Étape de plainte introuvable")
    pl["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.dossiers.update_one({"id": dossier_id},
                                 {"$set": {"plainte": pl, "updated_at": pl["updated_at"]}})
    await audit(dossier_id, user, f"Plainte — étape « {found['label']} »", body.statut or "")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


def _plainte_letter(d: dict, t: str) -> dict:
    nom = d.get("nom_entreprise", "")
    neq = d.get("neq") or "—"
    ref = (d.get("plainte") or {}).get("reference_oqlf") or "[référence OQLF]"
    today = datetime.now(timezone.utc).date().isoformat()
    sign = "[Votre nom et fonction]"
    if t == "accuse_reception":
        subject = f"Accusé de réception — plainte {ref} — {nom}"
        body = (f"Objet : Accusé de réception de votre communication (réf. {ref})\nDate : {today}\n\n"
                f"Madame, Monsieur,\n\n"
                f"Nous accusons réception de votre communication concernant l'entreprise {nom} (NEQ {neq}). "
                f"Nous prenons acte de la plainte et confirmons notre pleine collaboration.\n\n"
                f"Nous procédons à l'examen des éléments soulevés et reviendrons vers vous dans les meilleurs délais.\n\n"
                f"Veuillez agréer nos salutations distinguées.\n\n{sign}\n{nom}")
    elif t == "demande_delai":
        subject = f"Demande de délai — plainte {ref} — {nom}"
        body = (f"Objet : Demande de modification de l'échéancier (réf. {ref})\nDate : {today}\n\n"
                f"Madame, Monsieur,\n\n"
                f"Concernant la plainte visant l'entreprise {nom} (NEQ {neq}), nous nous engageons à apporter les "
                f"correctifs demandés. Compte tenu de [préciser les motifs : délais fournisseurs, refonte de "
                f"l'affichage, traduction de documents, etc.], nous sollicitons respectueusement un délai jusqu'au "
                f"[date proposée].\n\n"
                f"Nous demeurons disponibles pour convenir avec vous d'un échéancier acceptable.\n\n"
                f"Veuillez agréer nos salutations distinguées.\n\n{sign}\n{nom}")
    else:  # correctif_propose
        subject = f"Correctifs proposés — plainte {ref} — {nom}"
        body = (f"Objet : Mesures correctives proposées (réf. {ref})\nDate : {today}\n\n"
                f"Madame, Monsieur,\n\n"
                f"À la suite de la plainte visant l'entreprise {nom} (NEQ {neq}), nous proposons les mesures "
                f"correctives suivantes :\n"
                f"1. [Décrire le correctif] — échéance : [date]\n"
                f"2. [Décrire le correctif] — échéance : [date]\n\n"
                f"Ces mesures visent à assurer la conformité aux articles applicables de la Charte de la langue "
                f"française. Nous restons à votre disposition pour tout ajustement.\n\n"
                f"Veuillez agréer nos salutations distinguées.\n\n{sign}\n{nom}")
    return {"type": t, "subject": subject, "body": body}


@api.get("/dossiers/{dossier_id}/plainte/lettre")
async def plainte_letter(dossier_id: str, type: str = Query("accuse_reception"),
                         user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if type not in ("accuse_reception", "demande_delai", "correctif_propose"):
        raise HTTPException(status_code=400, detail="Type de lettre invalide")
    return _plainte_letter(d, type)


@api.get("/dossiers/{dossier_id}/export/plainte")
async def export_plainte(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if not d.get("plainte"):
        raise HTTPException(status_code=404, detail="Aucun dossier de plainte.")
    await audit(dossier_id, user, "Export PDF — Dossier de plainte")
    docs = await db.documents.find({"dossier_id": dossier_id, "is_deleted": False},
                                   {"_id": 0}).to_list(1000)
    pieces_by_stage: Dict[str, list] = {}
    for doc in docs:
        cat = doc.get("category") or ""
        if cat.startswith("plainte:"):
            pieces_by_stage.setdefault(cat.split(":", 1)[1], []).append(
                doc.get("original_filename", "Pièce"))
    from pdf_export import build_plainte_pdf
    buf = build_plainte_pdf(d, pieces_by_stage)
    fn = f"dossier_plainte_{d.get('neq') or dossier_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.put("/dossiers/{dossier_id}/req-declaration")
async def save_req_declaration(dossier_id: str, body: ReqDeclarationIn,
                               user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    total = d.get("nb_employes_quebec") or 0
    n = max(0, min(body.nb_employes_non_francophones, total))
    proportion = round((n / total) * 100, 1) if total else 0.0
    decl = {"nb_employes_non_francophones": n, "total_employes": total,
            "proportion_non_francophone": proportion,
            "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.dossiers.update_one({"id": dossier_id},
                                 {"$set": {"req_declaration": decl, "updated_at": decl["updated_at"]}})
    await audit(dossier_id, user,
                f"Déclaration REQ enregistrée : {n}/{total} employé(s) ne pouvant communiquer en français ({proportion} %)")
    updated = await db.dossiers.find_one({"id": dossier_id})
    return enrich_dossier(updated)


@api.put("/dossiers/{dossier_id}/parcours-a/profil")
async def save_parcours_a_profil(dossier_id: str, body: ParcoursAProfilIn,
                                 user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if (d.get("regime") or "B") != "A":
        raise HTTPException(status_code=400, detail="Réservé au régime des obligations universelles.")
    nb = max(0, body.nb_employes or 0)
    nbf = max(0, min(body.nb_francais or 0, nb))
    non_franco = nb - nbf
    proportion = round((non_franco / nb) * 100, 1) if nb else 0.0
    now = datetime.now(timezone.utc).isoformat()
    profil = {
        "neq": (body.neq or "").strip(),
        "nom_legal": (body.nom_legal or "").strip(),
        "marques": body.marques or [],
        "syndicat": bool(body.syndicat),
        "vend_produits": bool(body.vend_produits),
        "vend_jouets": bool(body.vend_jouets),
        "immo_residentiel": bool(body.immo_residentiel),
        "nb_employes": nb, "nb_francais": nbf,
        "req_preparatoire": {"non_francophones": non_franco, "proportion": proportion},
        "completed": True, "updated_at": now,
    }
    upd = {"parcours_a_profil": profil, "nb_employes_quebec": nb, "updated_at": now}
    if profil["neq"]:
        upd["neq"] = profil["neq"]
    if profil["nom_legal"]:
        upd["nom_entreprise"] = profil["nom_legal"]
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user,
                f"Profil Parcours A enregistré (syndicat={profil['syndicat']}, produits={profil['vend_produits']}, "
                f"jouets={profil['vend_jouets']}, immo={profil['immo_residentiel']}, {nbf}/{nb} en français)")
    updated = await db.dossiers.find_one({"id": dossier_id})
    return enrich_dossier(updated)


@api.get("/catalogue/u6/cnp-library")
async def get_cnp_library(user: dict = Depends(get_current_user)):
    from catalogue import CNP_TASK_LIBRARY
    return CNP_TASK_LIBRARY


@api.get("/dossiers/{dossier_id}/parcours-a/u6")
async def get_u6(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    return d.get("parcours_a_u6") or {"postes": []}


@api.put("/dossiers/{dossier_id}/parcours-a/u6")
async def save_u6(dossier_id: str, body: U6In, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if (d.get("regime") or "B") != "A":
        raise HTTPException(status_code=400, detail="Réservé au régime des obligations universelles.")
    now = datetime.now(timezone.utc).isoformat()
    payload = {"postes": body.postes, "updated_at": now}
    upd = {"parcours_a_u6": payload, "updated_at": now}
    # L'outil DOCUMENTE, il ne juge pas : on marque l'élément U6 « à valider » (jamais conforme auto).
    if body.postes:
        els = d.get("parcours_a_elements") or {}
        cur = els.get("U6", {})
        if cur.get("statut") in (None, "non_evalue"):
            cur["statut"] = "a_valider"
            cur["updated_at"] = now
            els["U6"] = cur
            upd["parcours_a_elements"] = els
    await db.dossiers.update_one({"id": dossier_id}, {"$set": upd})
    await audit(dossier_id, user, f"Outil U6 enregistré ({len(body.postes)} poste(s))")
    updated = await db.dossiers.find_one({"id": dossier_id})
    return enrich_dossier(updated)


@api.post("/dossiers/{dossier_id}/parcours-a/u6/motif-draft")
async def u6_motif_draft(dossier_id: str, body: U6MotifIn,
                         user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    from u6_ai import draft_motif
    try:
        draft = await draft_motif(body.poste)
    except Exception as e:
        logger.warning(f"U6 motif draft failed: {e}")
        raise HTTPException(status_code=502, detail="Rédaction IA indisponible pour le moment.")
    await audit(dossier_id, user, "Rédaction IA du motif d'offre (U6)")
    return {"draft": draft}


@api.get("/dossiers/{dossier_id}/parcours-a/u6/pdf")
async def u6_pdf(dossier_id: str, poste_id: str = Query(...),
                 user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    postes = ((d.get("parcours_a_u6") or {}).get("postes")) or []
    poste = next((p for p in postes if p.get("id") == poste_id), None)
    if not poste:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    from pdf_export import build_u6_pdf
    buf = build_u6_pdf(d, poste)
    await audit(dossier_id, user, f"Export PDF — dossier de démarche U6 ({poste.get('titre') or poste_id})")
    fn = f"demarche_u6_{(poste.get('titre') or 'poste')}_{d.get('neq') or dossier_id}.pdf".replace(" ", "_")
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.get("/dossiers/{dossier_id}/export/regime-a")
async def export_regime_a(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    await audit(dossier_id, user, "Export PDF — Rapport de conformité (obligations universelles)")
    docs = await db.documents.find({"dossier_id": dossier_id, "is_deleted": False},
                                   {"_id": 0}).to_list(1000)
    by_theme: Dict[str, list] = {}
    for doc in docs:
        source = doc.get("url") or doc.get("original_filename") or "Document"
        for el in (doc.get("analysis") or {}).get("elements", []):
            by_theme.setdefault(el.get("theme_id"), []).append({
                "constat": el.get("constat", ""), "source": source,
                "mesure_suggeree": el.get("mesure_suggeree", ""),
                "statut": el.get("statut", "a_valider")})
    from pdf_export import build_regime_a_pdf
    buf = build_regime_a_pdf(d, UNIVERSAL_THEMES, by_theme)
    fn = f"conformite_obligations_universelles_{d.get('neq') or dossier_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.get("/dossiers/{dossier_id}/export/module2")
async def export_module2(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    await audit(dossier_id, user, "Export PDF — Module 2 (Programme de francisation)")
    comite = (d.get("nb_employes_quebec") or 0) >= 100
    buf = build_module2_pdf(d, THEMES_LEGAUX, comite)
    fn = f"programme_francisation_{d.get('neq') or dossier_id}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@api.get("/dossiers/{dossier_id}/gantt/export")
async def export_gantt(dossier_id: str, kind: str = "parcours_a", format: str = "pdf",
                       user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    if kind not in ("parcours_a", "francisation"):
        raise HTTPException(status_code=400, detail="Type de Gantt invalide")
    if format not in ("pdf", "png"):
        raise HTTPException(status_code=400, detail="Format invalide")
    from pdf_export import build_gantt_pdf, gantt_pdf_to_png
    themes = UNIVERSAL_THEMES if kind == "parcours_a" else THEMES_LEGAUX
    d = enrich_dossier(d)
    pdf_buf = build_gantt_pdf(d, kind, themes)
    await audit(dossier_id, user, f"Export Gantt ({kind}, {format})")
    base = f"gantt_{kind}_{d.get('neq') or dossier_id}"
    if format == "png":
        png = gantt_pdf_to_png(pdf_buf)
        return StreamingResponse(png, media_type="image/png",
                                 headers={"Content-Disposition": f'attachment; filename="{base}.png"'})
    return StreamingResponse(pdf_buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{base}.pdf"'})


# ---------------------------------------------------------------- moteur d'analyse
class UrlIn(BaseModel):
    url: str


def theme_by_id(tid: str) -> Optional[dict]:
    return next((t for t in (THEMES_LEGAUX + UNIVERSAL_THEMES) if t["id"] == tid), None)


def serialize_doc(d: dict) -> dict:
    d.pop("_id", None)
    return d


async def get_owned_document(doc_id: str, user: dict) -> dict:
    doc = await db.documents.find_one({"id": doc_id, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    await get_owned_dossier(doc["dossier_id"], user)
    return doc


def _finding_status(theme_id: str, element: dict) -> str:
    t = theme_by_id(theme_id)
    if t and t.get("texte_loi_valide") and element.get("potentiellement_non_conforme"):
        return "non_conforme"
    return "a_valider"


ALLOWED_UPLOAD_EXT = {"pdf", "png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@api.post("/dossiers/{dossier_id}/documents")
async def upload_document(dossier_id: str, file: UploadFile = File(...),
                          category: Optional[str] = Query(None),
                          user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    ext = (file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "")
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(status_code=400, detail="Type de fichier non autorisé (PDF, PNG, JPEG, WEBP).")
    content_type = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (maximum 15 Mo).")
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    result = await run_in_threadpool(put_object, path, data, content_type)
    doc = {
        "id": str(uuid.uuid4()), "dossier_id": dossier_id, "type": "file",
        "kind": "image" if content_type.startswith("image/") else ("pdf" if ext == "pdf" else "file"),
        "original_filename": file.filename, "storage_path": result["path"],
        "content_type": content_type, "size": result.get("size", len(data)),
        "url": None, "analysis": None, "is_deleted": False,
        "category": category,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(dict(doc))
    await audit(dossier_id, user, "Téléversement d'un document", file.filename)
    return serialize_doc(doc)


@api.post("/dossiers/{dossier_id}/documents/url")
async def add_url_document(dossier_id: str, body: UrlIn,
                           user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    doc = {
        "id": str(uuid.uuid4()), "dossier_id": dossier_id, "type": "url", "kind": "url",
        "original_filename": body.url, "storage_path": None, "content_type": "text/html",
        "size": 0, "url": body.url, "analysis": None, "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(dict(doc))
    await audit(dossier_id, user, "Ajout d'une URL à analyser", body.url)
    return serialize_doc(doc)


@api.get("/dossiers/{dossier_id}/documents")
async def list_documents(dossier_id: str, user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    rows = await db.documents.find({"dossier_id": dossier_id, "is_deleted": False},
                                   {"_id": 0}).to_list(1000)
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows


@api.get("/documents/{doc_id}/download")
async def download_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await get_owned_document(doc_id, user)
    if not doc.get("storage_path"):
        raise HTTPException(status_code=400, detail="Ce document n'a pas de fichier stocké")
    data, ct = await run_in_threadpool(get_object, doc["storage_path"])
    return Response(content=data, media_type=doc.get("content_type") or ct)


@api.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await get_owned_document(doc_id, user)
    await db.documents.update_one({"id": doc_id}, {"$set": {"is_deleted": True}})
    await audit(doc["dossier_id"], user, "Suppression d'un document", doc.get("original_filename", ""))
    return {"ok": True}


async def _analyze_and_store(doc_id: str):
    """Analyse LLM d'un document et stockage du résultat (utilisé en tâche de fond)."""
    doc = await db.documents.find_one({"id": doc_id})
    if not doc or doc.get("is_deleted"):
        return
    _dossier = await db.dossiers.find_one({"id": doc["dossier_id"]})
    themes = themes_for_regime((_dossier or {}).get("regime"))
    try:
        if doc.get("type") == "url":
            text = await run_in_threadpool(analysis.fetch_url_text, doc["url"])
            result = await analysis.run_llm_analysis("text", text, themes, doc.get("original_filename", ""))
        elif doc.get("kind") == "image":
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            b64 = base64.b64encode(data).decode("utf-8")
            result = await analysis.run_llm_analysis("image", (b64, ct), themes, doc.get("original_filename", ""))
        elif doc.get("kind") == "pdf":
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            text = await run_in_threadpool(analysis.extract_pdf_text, data)
            result = await analysis.run_llm_analysis("text", text, themes, doc.get("original_filename", ""))
        else:
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            text = data.decode("utf-8", errors="ignore")
            result = await analysis.run_llm_analysis("text", text, themes, doc.get("original_filename", ""))
    except Exception as e:
        logger.warning(f"analyse auto échouée pour {doc_id}: {e}")
        return
    now_date = datetime.now(timezone.utc).date()
    for el in result.get("elements", []):
        el["id"] = str(uuid.uuid4())
        el["converti"] = False
        el["statut"] = _finding_status(el.get("theme_id"), el)
        jours = el.get("echeance_suggeree_jours")
        el["echeance_suggeree_date"] = (now_date + timedelta(days=jours)).isoformat() if isinstance(jours, int) else None
    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    await db.documents.update_one({"id": doc_id}, {"$set": {"analysis": result}})


@api.post("/documents/{doc_id}/analyze")
async def analyze_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await get_owned_document(doc_id, user)
    _dossier = await db.dossiers.find_one({"id": doc["dossier_id"]})
    themes = themes_for_regime((_dossier or {}).get("regime"))
    try:
        if doc["type"] == "url":
            text = await run_in_threadpool(analysis.fetch_url_text, doc["url"])
            result = await analysis.run_llm_analysis("text", text, themes, doc.get("original_filename", ""))
        elif doc.get("kind") == "image":
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            b64 = base64.b64encode(data).decode("utf-8")
            result = await analysis.run_llm_analysis("image", (b64, ct), themes, doc["original_filename"])
        elif doc.get("kind") == "pdf":
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            text = await run_in_threadpool(analysis.extract_pdf_text, data)
            result = await analysis.run_llm_analysis("text", text, themes, doc["original_filename"])
        else:
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            result = await analysis.run_llm_analysis("text", text, themes, doc["original_filename"])
    except HTTPException:
        raise
    except analysis.UrlValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analyse échouée pour {doc_id}: {e}")
        raise HTTPException(status_code=424, detail="L'analyse du document a échoué. Veuillez réessayer plus tard.")

    now_date = datetime.now(timezone.utc).date()
    for el in result.get("elements", []):
        el["id"] = str(uuid.uuid4())
        el["converti"] = False
        el["statut"] = _finding_status(el.get("theme_id"), el)
        jours = el.get("echeance_suggeree_jours")
        el["echeance_suggeree_date"] = (now_date + timedelta(days=jours)).isoformat() if isinstance(jours, int) else None
    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    await db.documents.update_one({"id": doc_id}, {"$set": {"analysis": result}})
    await audit(doc["dossier_id"], user, "Analyse d'un document",
                f"{doc.get('original_filename', '')} — {len(result.get('elements', []))} élément(s)")
    doc["analysis"] = result
    return serialize_doc(doc)


@api.get("/dossiers/{dossier_id}/plan-correction")
async def plan_correction(dossier_id: str, user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    docs = await db.documents.find({"dossier_id": dossier_id, "is_deleted": False},
                                   {"_id": 0}).to_list(1000)
    items = []
    for doc in docs:
        ana = doc.get("analysis") or {}
        source = doc.get("url") or doc.get("original_filename") or "Document"
        for el in ana.get("elements", []):
            t = theme_by_id(el.get("theme_id"))
            items.append({
                "finding_id": el.get("id"),
                "document_id": doc["id"],
                "source": source,
                "theme_id": el.get("theme_id"),
                "theme_nom": t["nom_theme"] if t else el.get("theme_id"),
                "texte_loi_valide": bool(t and t.get("texte_loi_valide")),
                "constat": el.get("constat", ""),
                "statut": el.get("statut", "a_valider"),
                "mesure_suggeree": el.get("mesure_suggeree", ""),
                "echeance_suggeree": el.get("echeance_suggeree_date"),
                "cout_approximatif": el.get("cout_approximatif", ""),
                "converti": bool(el.get("converti")),
            })
    return items


@api.post("/dossiers/{dossier_id}/plan-correction/{finding_id}/to-mesure")
async def finding_to_mesure(dossier_id: str, finding_id: str,
                            user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    docs = await db.documents.find({"dossier_id": dossier_id, "is_deleted": False}).to_list(1000)
    target_doc, target_el = None, None
    for doc in docs:
        for el in (doc.get("analysis") or {}).get("elements", []):
            if el.get("id") == finding_id:
                target_doc, target_el = doc, el
                break
        if target_el:
            break
    if not target_el:
        raise HTTPException(status_code=404, detail="Élément introuvable")

    jours = target_el.get("echeance_suggeree_jours")
    ech = ""
    if isinstance(jours, int):
        ech = (datetime.now(timezone.utc).date() + timedelta(days=jours)).isoformat()
    mesure = {
        "id": str(uuid.uuid4()), "theme_id": target_el.get("theme_id"),
        "mesure_engagee": target_el.get("mesure_suggeree", ""),
        "precisions_entreprise": target_el.get("constat", ""),
        "precisions_oqlf": "", "propositions_oqlf": "",
        "echeance": ech, "statut_mise_en_oeuvre": "a_faire",
        "source": "analyse",
        "external_legal_object_id": None, "external_source_type": None,
        "external_version_id": None, "external_citation": None,
        "reference_date": None, "retrieved_at": None,
    }
    mesures = d.get("module2_mesures", []) or []
    mesures.append(mesure)
    await db.dossiers.update_one({"id": dossier_id}, {"$set": {
        "module2_mesures": mesures, "updated_at": datetime.now(timezone.utc).isoformat()}})

    target_el["converti"] = True
    await db.documents.update_one({"id": target_doc["id"]},
                                  {"$set": {"analysis": target_doc["analysis"]}})
    await audit(dossier_id, user, "Conversion d'un constat en mesure (Module 2)",
                target_el.get("theme_id", ""))
    return {"mesure": mesure}


@api.get("/dossiers/{dossier_id}/courriel")
async def courriel_draft(dossier_id: str, module: int = Query(1),
                         user: dict = Depends(get_current_user)):
    d = enrich_dossier(await get_owned_dossier(dossier_id, user))
    nom = d.get("nom_entreprise", "")
    neq = d.get("neq", "—")
    if module == 2:
        objet = f"Programme de francisation — {nom} (NEQ {neq})"
        corps = (
            f"Bonjour,\n\n"
            f"Vous trouverez ci-joint le programme de francisation de l'entreprise {nom} "
            f"(NEQ {neq}), établi conformément à la Charte de la langue française.\n\n"
            f"Le document PDF est joint séparément à ce courriel.\n\n"
            f"Cordialement,\n{user.get('name', '')}"
        )
        pdf_path = f"/dossiers/{dossier_id}/export/module2"
        pdf_filename = f"programme_francisation_{neq}.pdf"
    else:
        objet = f"Analyse de la situation linguistique — {nom} (NEQ {neq})"
        ech = d.get("echeance_module1")
        corps = (
            f"Bonjour,\n\n"
            f"Vous trouverez ci-joint l'analyse de la situation linguistique de l'entreprise "
            f"{nom} (NEQ {neq})"
            + (f", à transmettre au plus tard le {ech}" if ech else "")
            + ".\n\nLe document PDF est joint séparément à ce courriel.\n\n"
            f"Cordialement,\n{user.get('name', '')}"
        )
        pdf_path = f"/dossiers/{dossier_id}/export/module1"
        pdf_filename = f"analyse_linguistique_{neq}.pdf"
    return {"to": "", "subject": objet, "body": corps,
            "pdf_path": pdf_path, "pdf_filename": pdf_filename}


# ---------------------------------------------------------------- Amorce mobile (QR)
AMORCE_TTL_MIN = 30
MOBILE_ACTOR = {"email": "amorce-mobile", "account_type": "mobile"}


class DeclarationIn(BaseModel):
    no_job_posting: Optional[bool] = None


def _amorce_effective_status(s: dict) -> str:
    if s.get("status") in ("completed", "revoked"):
        return s["status"]
    try:
        if datetime.fromisoformat(s["expires_at"]) < datetime.now(timezone.utc):
            return "expired"
    except Exception:
        pass
    return "active"


def _amorce_public(s: dict, dossier_nom: str = "") -> dict:
    return {
        "session_id": s["id"],
        "status": _amorce_effective_status(s),
        "dossier_nom": dossier_nom or s.get("dossier_nom", ""),
        "expires_at": s["expires_at"],
        "regime": s.get("regime", "B"),
        "questions": amorce.questions_for_regime(s.get("regime")),
        "photo_categories": amorce.photo_categories_for_regime(s.get("regime")),
        "answers": s.get("answers", {}),
        "answered_keys": list((s.get("answers") or {}).keys()),
        "photos": s.get("photos", []),
        "declarations": s.get("declarations", {}),
    }


async def _get_active_amorce(session_id: str) -> dict:
    s = await db.amorce_sessions.find_one({"id": session_id})
    if not s:
        raise HTTPException(status_code=404, detail="Session d'amorce introuvable.")
    st = _amorce_effective_status(s)
    if st == "revoked":
        raise HTTPException(status_code=410, detail="Ce lien a été révoqué.")
    if st == "completed":
        raise HTTPException(status_code=410, detail="Cette amorce est déjà complétée.")
    if st == "expired":
        raise HTTPException(status_code=410, detail="Ce lien a expiré. Demandez un nouveau code QR.")
    return s


@api.post("/dossiers/{dossier_id}/amorce/session")
async def create_amorce_session(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    await db.amorce_sessions.update_many(
        {"dossier_id": dossier_id, "status": "active"}, {"$set": {"status": "revoked"}})
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    s = {
        "id": token, "dossier_id": dossier_id, "owner_id": user["id"],
        "dossier_nom": d.get("nom_entreprise", ""),
        "regime": d.get("regime") or "B",
        "status": "active",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=AMORCE_TTL_MIN)).isoformat(),
        "opened_at": None, "completed_at": None,
        "photos": [], "answers": {}, "declarations": {},
    }
    await db.amorce_sessions.insert_one(dict(s))
    await audit(dossier_id, user, "Amorce mobile — génération d'un lien QR")
    out = _amorce_public(s, d.get("nom_entreprise", ""))
    out["mobile_path"] = f"/m/{token}"
    return out


@api.get("/dossiers/{dossier_id}/amorce/session")
async def get_amorce_session(dossier_id: str, user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    s = await db.amorce_sessions.find_one({"dossier_id": dossier_id}, sort=[("created_at", -1)])
    if not s:
        return {"status": "none"}
    return _amorce_public(s)


@api.post("/dossiers/{dossier_id}/amorce/session/revoke")
async def revoke_amorce_session(dossier_id: str, user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    await db.amorce_sessions.update_many(
        {"dossier_id": dossier_id, "status": "active"}, {"$set": {"status": "revoked"}})
    await audit(dossier_id, user, "Amorce mobile — révocation du lien QR")
    return {"ok": True}


async def _merge_amorce_answers(dossier_id: str) -> dict:
    """Fusionne les réponses de toutes les sessions d'amorce du dossier (la plus récente prime)."""
    merged = {}
    cursor = db.amorce_sessions.find({"dossier_id": dossier_id}).sort("created_at", 1)
    async for s in cursor:
        for k, v in (s.get("answers") or {}).items():
            merged[k] = v
    return merged


@api.get("/dossiers/{dossier_id}/amorce/proposals")
async def amorce_module1_proposals(dossier_id: str, user: dict = Depends(get_current_user)):
    await get_owned_dossier(dossier_id, user)
    answers = await _merge_amorce_answers(dossier_id)
    if not answers:
        return {"proposals": [], "warnings": ["Aucune réponse vocale d'amorce n'est disponible pour ce dossier."]}
    proposals = amorce.build_module1_proposals(answers)
    await audit(dossier_id, user, "Report de l'entrevue vocale (amorce) vers le Module 1")
    return {"proposals": proposals, "warnings": []}


@api.get("/dossiers/{dossier_id}/diagnostic")
async def get_dossier_diagnostic(dossier_id: str, user: dict = Depends(get_current_user)):
    d = await get_owned_dossier(dossier_id, user)
    m1 = dict(d.get("module1_data") or {})
    # repli sur l'amorce : préremplit les clés manquantes à partir des réponses vocales
    answers = await _merge_amorce_answers(dossier_id)
    for p in amorce.build_module1_proposals(answers):
        m1.setdefault(p["key"], p["value"])
    employes = diagnostic._num(m1.get("s4.employes_quebec"))
    if employes is None:
        employes = d.get("nb_employes_quebec") or 0
    else:
        employes = int(employes)
    jours = d.get("jours_restants_module1")
    docs = await db.documents.find({"dossier_id": dossier_id, "is_deleted": {"$ne": True}}).to_list(500)
    signals = diagnostic.derive_conformite_signals(docs)
    return diagnostic.compute_diagnostic(m1, employes, jours, signals)


# ---- routes publiques (téléphone, jeton dans l'URL, sans login)
@api.get("/amorce/{session_id}")
async def amorce_public_info(session_id: str):
    s = await db.amorce_sessions.find_one({"id": session_id})
    if not s:
        raise HTTPException(status_code=404, detail="Session d'amorce introuvable.")
    if s.get("status") == "active" and not s.get("opened_at") and _amorce_effective_status(s) == "active":
        await db.amorce_sessions.update_one(
            {"id": session_id}, {"$set": {"opened_at": datetime.now(timezone.utc).isoformat()}})
        await audit(s["dossier_id"], MOBILE_ACTOR, "Amorce mobile — session ouverte sur le téléphone")
    return _amorce_public(s)


@api.post("/amorce/{session_id}/photo")
async def amorce_upload_photo(session_id: str, background: BackgroundTasks,
                              category: str = Query(...), file: UploadFile = File(...)):
    s = await _get_active_amorce(session_id)
    label = next((c["label"] for c in amorce.AMORCE_PHOTO_CATEGORIES if c["key"] == category), category)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Photo trop volumineuse (maximum 15 Mo).")
    ct = file.content_type or "image/jpeg"
    ext = amorce.ext_from_content_type(ct, "jpg")
    path = f"{APP_NAME}/amorce/{s['owner_id']}/{uuid.uuid4()}.{ext}"
    res = await run_in_threadpool(put_object, path, data, ct)
    doc = {
        "id": str(uuid.uuid4()), "dossier_id": s["dossier_id"], "type": "file", "kind": "image",
        "original_filename": f"Amorce — {label}", "storage_path": res["path"],
        "content_type": ct, "size": res.get("size", len(data)), "url": None,
        "source": "amorce-photo", "category": category, "analysis": None, "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(dict(doc))
    entry = {"category": category, "label": label, "document_id": doc["id"],
             "created_at": doc["created_at"]}
    await db.amorce_sessions.update_one({"id": session_id}, {"$push": {"photos": entry}})
    if category in amorce.AMORCE_ANALYZE_CATS:
        background.add_task(_analyze_and_store, doc["id"])
    return {"ok": True, "document_id": doc["id"], "category": category, "label": label}


@api.post("/amorce/{session_id}/audio")
async def amorce_upload_audio(session_id: str, question_key: str = Query(...),
                              file: UploadFile = File(...)):
    s = await _get_active_amorce(session_id)
    q = next((x for x in amorce.AMORCE_QUESTIONS if x["key"] == question_key), None)
    if not q:
        raise HTTPException(status_code=400, detail="Question inconnue.")
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Enregistrement trop volumineux (maximum 25 Mo).")
    ct = file.content_type or "audio/webm"
    ext = amorce.ext_from_content_type(ct, "webm")
    path = f"{APP_NAME}/amorce/{s['owner_id']}/{uuid.uuid4()}.{ext}"
    res = await run_in_threadpool(put_object, path, data, ct)
    audio_doc = {
        "id": str(uuid.uuid4()), "dossier_id": s["dossier_id"], "type": "file", "kind": "audio",
        "original_filename": f"Amorce (audio) — {q['question'][:60]}", "storage_path": res["path"],
        "content_type": ct, "size": res.get("size", len(data)), "url": None,
        "source": "amorce-audio", "question_key": question_key, "analysis": None, "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(dict(audio_doc))

    text, lang, warning = "", None, None
    try:
        text, lang = await amorce.transcribe_audio(data, f"audio.{ext}")
    except Exception as e:
        logger.warning(f"amorce transcription failed ({session_id}): {e}")
        warning = "La transcription a échoué ; l'audio a été conservé. Vous pourrez saisir la réponse plus tard."
    fr = await amorce.translate_to_french(text, q["question"]) if text else ""

    answer = {
        "question": q["question"], "field": q["field"],
        "transcript_original": text, "lang": lang, "transcript_fr": fr,
        "audio_document_id": audio_doc["id"], "optional": q.get("optional", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.amorce_sessions.update_one({"id": session_id}, {"$set": {f"answers.{question_key}": answer}})
    return {"ok": True, "question_key": question_key, "transcript_original": text,
            "lang": lang, "transcript_fr": fr, "warning": warning}


@api.post("/amorce/{session_id}/declaration")
async def amorce_declaration(session_id: str, body: DeclarationIn):
    s = await _get_active_amorce(session_id)
    upd = {}
    if body.no_job_posting is not None:
        upd["declarations.no_job_posting"] = body.no_job_posting
    if upd:
        await db.amorce_sessions.update_one({"id": session_id}, {"$set": upd})
    return {"ok": True}


@api.post("/amorce/{session_id}/complete")
async def amorce_complete(session_id: str):
    s = await _get_active_amorce(session_id)
    await db.amorce_sessions.update_one({"id": session_id}, {"$set": {
        "status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}})
    await audit(s["dossier_id"], MOBILE_ACTOR, "Amorce mobile — session complétée depuis le téléphone")
    return {"ok": True}


# ---------------------------------------------------------------- notifications / rappels
async def generate_reminders():
    dossiers = await db.dossiers.find({}).to_list(5000)
    created = 0
    for d in dossiers:
        de = enrich_dossier(dict(d))
        jours = de.get("jours_restants_module1")
        ech = de.get("echeance_module1")
        # Rappels liés à une plainte ouverte (échéances des étapes)
        if de.get("plainte_ouverte") and de.get("plainte_jours") is not None:
            pj = de["plainte_jours"]; pe = de.get("plainte_echeance")
            if pj < 0:
                ptyp, pmsg = "plainte_retard", f"Plainte en retard : une échéance de « {d.get('nom_entreprise','')} » était due le {pe}."
            elif pj <= 7:
                ptyp, pmsg = "plainte_j7", f"Plainte : échéance imminente pour « {d.get('nom_entreprise','')} » dans {pj} jour(s) ({pe})."
            elif pj <= 30:
                ptyp, pmsg = "plainte_j30", f"Plainte : échéance à venir pour « {d.get('nom_entreprise','')} » dans {pj} jours ({pe})."
            else:
                ptyp = None
            if ptyp and not await db.notifications.find_one({"dossier_id": d["id"], "type": ptyp}):
                try:
                    await db.notifications.insert_one({
                        "id": str(uuid.uuid4()), "owner_id": d["owner_id"], "dossier_id": d["id"],
                        "dossier_nom": d.get("nom_entreprise", ""), "type": ptyp, "jours": pj,
                        "echeance": pe, "message": pmsg, "read": False,
                        "created_at": datetime.now(timezone.utc).isoformat()})
                    created += 1
                    owner = await db.users.find_one({"_id": ObjectId(d["owner_id"])})
                    if owner and owner.get("email"):
                        await mailer.send_reminder_email(owner["email"], d.get("nom_entreprise", ""), pmsg, d["id"])
                except DuplicateKeyError:
                    pass
                except Exception as ee:
                    logger.warning(f"Rappel de plainte échoué (dossier {d['id']}): {ee}")
        if jours is None:
            continue
        if 0 <= jours <= 7:
            typ, message = "j7", f"Échéance imminente : l'analyse linguistique de « {d.get('nom_entreprise','')} » est due dans {jours} jour(s) ({ech})."
        elif 7 < jours <= 30:
            typ, message = "j30", f"Rappel : l'analyse linguistique de « {d.get('nom_entreprise','')} » est due dans {jours} jours ({ech})."
        elif jours < 0:
            typ, message = "retard", f"En retard : l'analyse linguistique de « {d.get('nom_entreprise','')} » était due le {ech}."
        else:
            continue
        if await db.notifications.find_one({"dossier_id": d["id"], "type": typ}):
            continue
        try:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()), "owner_id": d["owner_id"], "dossier_id": d["id"],
                "dossier_nom": d.get("nom_entreprise", ""), "type": typ, "jours": jours,
                "echeance": ech, "message": message, "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            created += 1
        except DuplicateKeyError:
            continue
        # Rappel aussi par courriel (en plus de la notification dans l'app).
        try:
            owner = await db.users.find_one({"_id": ObjectId(d["owner_id"])})
            if owner and owner.get("email"):
                await mailer.send_reminder_email(owner["email"], d.get("nom_entreprise", ""), message, d["id"])
        except Exception as ee:
            logger.warning(f"Courriel de rappel échoué (dossier {d['id']}): {ee}")
    logger.info(f"Rappels générés : {created}")
    return created


@api.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    rows = await db.notifications.find({"owner_id": user["id"]}, {"_id": 0}).to_list(200)
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows[:50]


@api.post("/notifications/{nid}/read")
async def read_notification(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "owner_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/notifications/read-all")
async def read_all_notifications(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"owner_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/cron/reminders")
async def cron_reminders(request: Request, background_tasks: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not secret or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Non autorisé")
    background_tasks.add_task(generate_reminders)
    return {"status": "accepted"}


async def generate_weekly_summary():
    """Envoie à chaque consultant PRO un résumé des échéances à venir (30 j) ou en retard."""
    users = await db.users.find({"account_type": "PRO"}).to_list(5000)
    sent = 0
    for u in users:
        owner_id = str(u["_id"])
        dossiers = await db.dossiers.find({"owner_id": owner_id}).to_list(5000)
        items = []
        for d in dossiers:
            de = enrich_dossier(dict(d))
            jours = de.get("jours_restants_module1")
            if jours is not None and jours <= 30:
                items.append({"nom": d.get("nom_entreprise", ""),
                              "echeance": de.get("echeance_module1"), "jours": jours})
            pj = de.get("plainte_jours")
            if de.get("plainte_ouverte") and pj is not None and pj <= 30:
                items.append({"nom": (d.get("nom_entreprise", "") or "") + " — plainte",
                              "echeance": de.get("plainte_echeance"), "jours": pj})
        if not items:
            continue
        items.sort(key=lambda x: x["jours"])
        try:
            if u.get("email"):
                await mailer.send_weekly_summary_email(u["email"], u.get("name", ""),
                                                       items, len(dossiers))
                sent += 1
        except Exception as ee:
            logger.warning(f"Résumé hebdomadaire échoué (owner {owner_id}): {ee}")
    logger.info(f"Résumés hebdomadaires envoyés : {sent}")
    return sent


@api.post("/cron/weekly-summary")
async def cron_weekly_summary(request: Request, background_tasks: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not secret or not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Non autorisé")
    background_tasks.add_task(generate_weekly_summary)
    return {"status": "accepted"}


# ---------------------------------------------------------------- startup
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.dossiers.create_index("owner_id")
    await db.clients.create_index("owner_id")
    await db.audit_logs.create_index("dossier_id")
    await db.login_attempts.create_index("identifier", unique=True)
    await db.documents.create_index("dossier_id")
    await db.notifications.create_index([("dossier_id", 1), ("type", 1)], unique=True)
    await db.notifications.create_index("owner_id")
    await db.amorce_sessions.create_index("dossier_id")
    await db.amorce_sessions.create_index("id", unique=True)
    try:
        init_storage()
        logger.info("Stockage d'objets initialisé.")
    except Exception as e:
        logger.error(f"Échec init stockage : {e}")
    # seed owner account
    admin_email = os.environ.get("ADMIN_EMAIL", "").lower()
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "")
    if admin_email and admin_pwd:
        existing = await db.users.find_one({"email": admin_email})
        if existing is None:
            await db.users.insert_one({
                "email": admin_email, "password_hash": hash_password(admin_pwd),
                "name": os.environ.get("ADMIN_NAME", "Admin"),
                "account_type": os.environ.get("ADMIN_ACCOUNT_TYPE", "PRO"),
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat()})
        elif not verify_password(admin_pwd, existing["password_hash"]):
            await db.users.update_one({"email": admin_email},
                                      {"$set": {"password_hash": hash_password(admin_pwd)}})
    logger.info("CONFORMISTE API prête.")


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
