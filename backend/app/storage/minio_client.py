"""
MinIO storage adapter — private S3-compatible object storage.

Security properties:
- Bucket is PRIVATE: no anonymous access, no public listing
- Object keys are random UUIDs — never the original filename
- Object keys are NEVER returned to the client
- Backend service credentials are the only credentials that can read/write
- Files are stored encrypted (done by caller before calling put_object)
- No presigned URLs — all access through this adapter, called after fresh authz check
"""

import io
import uuid
from collections.abc import Iterator
from functools import lru_cache

import structlog
from minio import Minio
from minio.error import S3Error

from app.config import get_settings

logger = structlog.get_logger(__name__)

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks for streaming


@lru_cache(maxsize=1)
def _get_client() -> Minio:
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _get_bucket() -> str:
    return get_settings().minio_bucket


def ensure_bucket_exists() -> None:
    """
    Create the private bucket if it doesn't exist.
    Called at application startup.
    The bucket policy is set to private (no public access).
    """
    client = _get_client()
    bucket = _get_bucket()
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("minio_bucket_created", bucket=bucket)
            # Bucket is private by default in MinIO — no need to set policy explicitly
            # but we set it explicitly to be safe
            _set_private_bucket_policy(client, bucket)
        else:
            logger.info("minio_bucket_exists", bucket=bucket)
    except S3Error as exc:
        logger.error("minio_bucket_setup_failed", error=str(exc))
        raise


def _set_private_bucket_policy(client: Minio, bucket: str) -> None:
    """
    Set the bucket policy to deny all public access.
    This is belt-and-suspenders — the bucket should be private by default.
    """
    import json
    # Explicit deny-all public policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyPublicAccess",
                "Effect": "Deny",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    f"arn:aws:s3:::{bucket}",
                    f"arn:aws:s3:::{bucket}/*",
                ],
                "Condition": {
                    "StringNotEquals": {
                        "aws:PrincipalArn": "arn:aws:iam::*:root"  # only service account
                    }
                },
            }
        ],
    }
    try:
        client.set_bucket_policy(bucket, json.dumps(policy))
    except S3Error as exc:
        # Non-fatal — bucket is already private by default
        logger.warning("minio_policy_set_failed", error=str(exc))


def generate_object_key() -> str:
    """
    Generate a random, unguessable object key.
    Never uses the original filename or document ID as the key.
    """
    return str(uuid.uuid4())


def put_object(object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """
    Store encrypted bytes in MinIO under the given object key.
    data should already be encrypted before calling this.
    """
    client = _get_client()
    bucket = _get_bucket()
    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.debug("minio_put_object", key_length=len(object_key), size=len(data))
    except S3Error as exc:
        logger.error("minio_put_failed", error=str(exc))
        raise


def get_object_bytes(object_key: str) -> bytes:
    """
    Retrieve encrypted bytes from MinIO.
    Caller is responsible for decrypting.
    Object key is NEVER from client input — always from DB lookup after authz check.
    """
    client = _get_client()
    bucket = _get_bucket()
    try:
        response = client.get_object(bucket_name=bucket, object_name=object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as exc:
        logger.error("minio_get_failed", error=str(exc))
        raise


def delete_object(object_key: str) -> None:
    """
    Delete an object from MinIO. Called when a document is purged.
    Only callable by the backend — never by client request directly.
    """
    client = _get_client()
    bucket = _get_bucket()
    try:
        client.remove_object(bucket_name=bucket, object_name=object_key)
        logger.info("minio_object_deleted", key_length=len(object_key))
    except S3Error as exc:
        logger.error("minio_delete_failed", error=str(exc))
        raise


def health_check() -> bool:
    """Check MinIO connectivity. Used by /health/ready endpoint."""
    try:
        client = _get_client()
        client.bucket_exists(_get_bucket())
        return True
    except Exception as exc:
        logger.warning("minio_health_check_failed", error=str(exc))
        return False
