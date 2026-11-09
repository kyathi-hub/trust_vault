"""
Local filesystem storage adapter — development only.
Replaces MinIO for local testing without Docker.
Files stored in ./dev_storage/
"""

import os
import uuid

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


def _storage_path() -> str:
    path = get_settings().local_storage_path
    os.makedirs(path, exist_ok=True)
    return path


def ensure_bucket_exists() -> None:
    os.makedirs(_storage_path(), exist_ok=True)
    logger.info("local_storage_ready", path=_storage_path())


def generate_object_key() -> str:
    return str(uuid.uuid4())


def put_object(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    path = os.path.join(_storage_path(), object_key)
    with open(path, "wb") as f:
        f.write(data)
    logger.debug("local_storage_put", key=object_key, size=len(data))


def get_object_bytes(object_key: str) -> bytes:
    path = os.path.join(_storage_path(), object_key)
    with open(path, "rb") as f:
        return f.read()


def delete_object(object_key: str) -> None:
    path = os.path.join(_storage_path(), object_key)
    if os.path.exists(path):
        os.remove(path)


def health_check() -> bool:
    return os.path.isdir(_storage_path())
