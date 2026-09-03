from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict

import jwt
import bcrypt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from dateutil.relativedelta import relativedelta

from catalogue import THEMES_LEGAUX, PIPELINE_STAGES
from pdf_export import build_module1_pdf, build_module2_pdf

# ---------------------------------------------------------------- DB / app
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="CONFORMISTE API")
api = APIRouter(prefix="/api")

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
    date_attestation_inscription: Optional[str] = None  # ISO date


class Module1In(BaseModel):
    module1_data: Dict[str, Any] = {}
    module1_meta: Dict[str, Any] = {}


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


def urgence_for(days: Optional[int]) -> str:
    if days is None:
        return "normal"
    if days <= 7:
        return "critical"
    if days <= 30:
        return "approaching"
    return "normal"


def enrich_dossier(d: dict) -> dict:
    d.pop("_id", None)
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
    token = create_access_token(uid, email)
    set_auth_cookie(response, token)
    return {"access_token": token,
            "user": {"id": uid, "email": email, "name": body.name,
                     "account_type": body.account_type}}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
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
async def get_themes(user: dict = Depends(get_current_user)):
    return THEMES_LEGAUX


@api.get("/catalogue/stages")
async def get_stages(user: dict = Depends(get_current_user)):
    return PIPELINE_STAGES


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
    doc = {
        "id": str(uuid.uuid4()), "owner_id": user["id"], "client_id": body.client_id,
        "nom_entreprise": body.nom_entreprise, "neq": body.neq,
        "nb_employes_quebec": body.nb_employes_quebec,
        "nb_etablissements": body.nb_etablissements,
        "date_attestation_inscription": body.date_attestation_inscription,
        "stages": new_dossier_stages(),
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
    await db.dossiers.update_one({"id": dossier_id}, {"$set": {
        "module2_admin": body.module2_admin, "module2_mesures": body.module2_mesures,
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    await audit(dossier_id, user, "Enregistrement du Module 2 (Programme de francisation)")
    return enrich_dossier(await get_owned_dossier(dossier_id, user))


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
    buf = build_module1_pdf(d)
    fn = f"analyse_linguistique_{d.get('neq') or dossier_id}.pdf"
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


# ---------------------------------------------------------------- startup
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.dossiers.create_index("owner_id")
    await db.clients.create_index("owner_id")
    await db.audit_logs.create_index("dossier_id")
    await db.login_attempts.create_index("identifier", unique=True)
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
