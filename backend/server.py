from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import uuid
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict

import jwt
import bcrypt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Header, Query
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from dateutil.relativedelta import relativedelta

from catalogue import THEMES_LEGAUX, PIPELINE_STAGES
from pdf_export import build_module1_pdf, build_module2_pdf
from storage import put_object, get_object, init_storage, APP_NAME, MIME_TYPES
import analysis

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


# ---------------------------------------------------------------- moteur d'analyse
class UrlIn(BaseModel):
    url: str


def theme_by_id(tid: str) -> Optional[dict]:
    return next((t for t in THEMES_LEGAUX if t["id"] == tid), None)


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


@api.post("/documents/{doc_id}/analyze")
async def analyze_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await get_owned_document(doc_id, user)
    try:
        if doc["type"] == "url":
            text = await run_in_threadpool(analysis.fetch_url_text, doc["url"])
            result = await analysis.run_llm_analysis("text", text, THEMES_LEGAUX, doc.get("original_filename", ""))
        elif doc.get("kind") == "image":
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            b64 = base64.b64encode(data).decode("utf-8")
            result = await analysis.run_llm_analysis("image", (b64, ct), THEMES_LEGAUX, doc["original_filename"])
        elif doc.get("kind") == "pdf":
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            text = await run_in_threadpool(analysis.extract_pdf_text, data)
            result = await analysis.run_llm_analysis("text", text, THEMES_LEGAUX, doc["original_filename"])
        else:
            data, ct = await run_in_threadpool(get_object, doc["storage_path"])
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            result = await analysis.run_llm_analysis("text", text, THEMES_LEGAUX, doc["original_filename"])
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


# ---------------------------------------------------------------- startup
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.dossiers.create_index("owner_id")
    await db.clients.create_index("owner_id")
    await db.audit_logs.create_index("dossier_id")
    await db.login_attempts.create_index("identifier", unique=True)
    await db.documents.create_index("dossier_id")
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
