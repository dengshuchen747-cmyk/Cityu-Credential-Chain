import hashlib
import re
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def save_evidence(file: UploadFile, wallet: str) -> tuple[str, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Evidence must be PDF, JPEG or PNG")

    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Evidence file is too large")
    if not content:
        raise HTTPException(status_code=422, detail="Evidence file is empty")

    wallet_dir = settings.upload_path / wallet.lower()
    wallet_dir.mkdir(parents=True, exist_ok=True)
    original = SAFE_NAME.sub("_", Path(file.filename or "evidence").name)
    stored_name = f"{secrets.token_hex(8)}-{original}"
    destination = wallet_dir / stored_name
    destination.write_bytes(content)
    digest = "0x" + hashlib.sha256(content).hexdigest()
    return str(destination.relative_to(settings.upload_path)), digest
