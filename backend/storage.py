"""Stockage d'objets.

Deux implémentations, sélectionnées par la présence des variables S3 :
- **S3 / compatible S3** (AWS S3 ou Cloudflare R2) : utilisé dès que S3_BUCKET,
  S3_ACCESS_KEY et S3_SECRET_KEY sont configurés (cible Railway, indépendant d'Emergent).
- **Repli Emergent** (proxy géré) : conservé tant que le stockage S3 n'est pas configuré,
  pour ne pas casser l'environnement de prévisualisation.

Comportement observable identique : `put_object(path, data, content_type)` renvoie
{"path", "size"} ; `get_object(path)` renvoie (bytes, content_type) ; retry/backoff
sur erreurs transitoires.
"""
import os
import io
import time
import logging
import requests

logger = logging.getLogger("conformiste.storage")

APP_NAME = "conformiste"

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
    "json": "application/json", "csv": "text/csv", "txt": "text/plain",
}

# ---- Configuration S3 / R2
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_REGION = os.environ.get("S3_REGION")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")  # requis pour Cloudflare R2

_USE_S3 = bool(S3_BUCKET and S3_ACCESS_KEY and S3_SECRET_KEY)

# ---- Configuration repli Emergent
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")

_s3_client = None
_storage_key = None


def _s3():
    global _s3_client
    if _s3_client is None:
        import boto3
        from botocore.config import Config
        _s3_client = boto3.client(
            "s3",
            region_name=S3_REGION,
            endpoint_url=S3_ENDPOINT_URL or None,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        )
    return _s3_client


def init_storage(force: bool = False):
    """Initialise le backend. Pour S3, vérifie l'accès au bucket ; sinon init Emergent."""
    if _USE_S3:
        _s3().head_bucket(Bucket=S3_BUCKET)
        return "s3"
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    if _USE_S3:
        last = None
        for attempt in range(3):
            try:
                _s3().put_object(Bucket=S3_BUCKET, Key=path, Body=data, ContentType=content_type)
                return {"path": path, "size": len(data)}
            except Exception as e:  # retry/backoff sur erreurs transitoires
                last = e
                if attempt < 2:
                    time.sleep(0.6 * (attempt + 1))
        raise last
    # ---- repli Emergent
    key = init_storage()
    for attempt in range(3):
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
        if resp.status_code == 404:
            key = init_storage(force=True)
            continue
        if resp.status_code in (502, 503) and attempt < 2:
            time.sleep(0.6 * (attempt + 1))
            continue
        break
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    if _USE_S3:
        last = None
        for attempt in range(3):
            try:
                obj = _s3().get_object(Bucket=S3_BUCKET, Key=path)
                return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")
            except Exception as e:
                last = e
                if attempt < 2:
                    time.sleep(0.6 * (attempt + 1))
        raise last
    # ---- repli Emergent
    key = init_storage()
    for attempt in range(3):
        resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key}, timeout=60)
        if resp.status_code == 404:
            key = init_storage(force=True)
            resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                                headers={"X-Storage-Key": key}, timeout=60)
        if resp.status_code in (502, 503) and attempt < 2:
            time.sleep(0.6 * (attempt + 1))
            continue
        break
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
