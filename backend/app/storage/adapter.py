"""
Storage adapter — switches between local filesystem (dev) and MinIO (production).
Import from here instead of minio_client or local_storage directly.
"""
from app.config import get_settings


def _local():
    from app.storage import local_storage
    return local_storage


def _minio():
    from app.storage import minio_client
    return minio_client


def _backend():
    return _local() if get_settings().use_local_storage else _minio()


def ensure_bucket_exists() -> None:
    _backend().ensure_bucket_exists()


def generate_object_key() -> str:
    return _backend().generate_object_key()


def put_object(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    _backend().put_object(object_key, data, content_type)


def get_object_bytes(object_key: str) -> bytes:
    return _backend().get_object_bytes(object_key)


def delete_object(object_key: str) -> None:
    _backend().delete_object(object_key)


def health_check() -> bool:
    return _backend().health_check()
