"""Emergent-managed object storage helpers (voir playbook object storage)."""
import os
import time
import requests

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "conformiste"

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
    "json": "application/json", "csv": "text/csv", "txt": "text/plain",
}

_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
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
