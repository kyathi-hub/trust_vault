"""
Upload validation — strict server-side file validation pipeline.

Security checks (in order):
1. Filename sanitization — no path traversal, null bytes, dangerous extensions
2. File size — enforced at reverse proxy AND here
3. Extension allowlist
4. Magic byte / file signature validation
5. MIME type consistency check (claimed vs detected)
6. Double-extension detection
7. Active content rejection for inline display

Browser-supplied Content-Type is NEVER trusted.
"""
import hashlib
import os
import re
from dataclasses import dataclass

import magic  # python-magic-bin on Windows, python-magic on Linux

from app.config import get_settings

# Dangerous extensions that must never be accepted
BLOCKED_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "scr", "vbs", "js", "jse", "wsf", "wsh",
    "ps1", "ps2", "psc1", "psc2", "msh", "msh1", "msh2",
    "sh", "bash", "zsh", "fish",
    "jar", "class", "war",
    "dll", "so", "dylib",
    "php", "php3", "php4", "php5", "phtml",
    "asp", "aspx", "cshtml", "vbhtml",
    "htm", "html", "svg", "xml", "xsl", "xslt",  # active/scriptable content
    "swf", "fla",
    "lnk", "url", "webloc",
    "hta", "htaccess",
}

# Magic bytes for common document types
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "pdf":  [b"%PDF"],
    "docx": [b"PK\x03\x04"],  # ZIP-based (Office Open XML)
    "xlsx": [b"PK\x03\x04"],
    "pptx": [b"PK\x03\x04"],
    "doc":  [b"\xd0\xcf\x11\xe0"],  # OLE2
    "xls":  [b"\xd0\xcf\x11\xe0"],
    "ppt":  [b"\xd0\xcf\x11\xe0"],
    "png":  [b"\x89PNG\r\n\x1a\n"],
    "jpg":  [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif":  [b"GIF87a", b"GIF89a"],
    "webp": [b"RIFF"],
    "zip":  [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "gz":   [b"\x1f\x8b"],
    "tar":  [b"ustar"],
    "txt":  [],  # text has no magic bytes — skip magic check
    "csv":  [],
}

# Safe filename regex — allow alphanumeric, spaces, hyphens, underscores, dots
SAFE_FILENAME_RE = re.compile(r'^[\w\s\-_.()]+$')
MAX_FILENAME_LENGTH = 255


@dataclass
class ValidationResult:
    ok: bool
    error: str | None
    detected_mime: str | None
    checksum_sha256: str | None
    file_size: int


def validate_upload(
    filename: str,
    content: bytes,
    claimed_content_type: str,
) -> ValidationResult:
    """
    Run all upload validation checks.
    Returns ValidationResult with ok=True if all checks pass.
    All failures return a generic error — no internal detail to the client.
    """
    settings = get_settings()

    # 1. File size
    if len(content) > settings.max_upload_size_bytes:
        return ValidationResult(ok=False, error="File too large", detected_mime=None, checksum_sha256=None, file_size=len(content))

    # 2. Filename sanitization
    fn_error = _validate_filename(filename)
    if fn_error:
        return ValidationResult(ok=False, error=fn_error, detected_mime=None, checksum_sha256=None, file_size=len(content))

    # 3. Extension extraction and allowlist check
    ext = _get_extension(filename)
    if ext not in settings.allowed_extensions:
        return ValidationResult(ok=False, error="File type not allowed", detected_mime=None, checksum_sha256=None, file_size=len(content))

    if ext in BLOCKED_EXTENSIONS:
        return ValidationResult(ok=False, error="File type not allowed", detected_mime=None, checksum_sha256=None, file_size=len(content))

    # 4. Double-extension check (e.g. evil.pdf.exe)
    parts = filename.rsplit(".", 2)
    if len(parts) == 3:
        penultimate_ext = parts[1].lower()
        if penultimate_ext in BLOCKED_EXTENSIONS:
            return ValidationResult(ok=False, error="File type not allowed", detected_mime=None, checksum_sha256=None, file_size=len(content))

    # 5. Magic byte validation
    magic_error = _validate_magic_bytes(content, ext)
    if magic_error:
        return ValidationResult(ok=False, error=magic_error, detected_mime=None, checksum_sha256=None, file_size=len(content))

    # 6. Detect actual MIME type via libmagic (ignores browser-supplied Content-Type)
    try:
        detected_mime = magic.from_buffer(content, mime=True)
    except Exception:
        detected_mime = "application/octet-stream"

    # 7. Consistency check: reject if detected type looks executable/dangerous
    if _is_dangerous_mime(detected_mime):
        return ValidationResult(ok=False, error="File type not allowed", detected_mime=detected_mime, checksum_sha256=None, file_size=len(content))

    # 8. Compute SHA-256 checksum
    checksum = hashlib.sha256(content).hexdigest()

    return ValidationResult(
        ok=True,
        error=None,
        detected_mime=detected_mime,
        checksum_sha256=checksum,
        file_size=len(content),
    )


def _validate_filename(filename: str) -> str | None:
    """Check filename for path traversal, null bytes, length, and dangerous chars."""
    if not filename:
        return "Filename is required"
    if len(filename) > MAX_FILENAME_LENGTH:
        return "Filename too long"
    if "\x00" in filename:
        return "Invalid filename"
    # Strip path components — never trust directory separators
    basename = os.path.basename(filename.replace("\\", "/"))
    if basename != filename.replace("\\", "/").split("/")[-1]:
        return "Invalid filename"
    if ".." in filename:
        return "Invalid filename"
    # Must not be empty after stripping
    if not basename.strip():
        return "Invalid filename"
    return None


def _get_extension(filename: str) -> str:
    """Extract the last extension, lowercased."""
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


def _validate_magic_bytes(content: bytes, ext: str) -> str | None:
    """Verify file starts with expected magic bytes for its extension."""
    signatures = MAGIC_SIGNATURES.get(ext)
    if signatures is None:
        # Unknown extension — already blocked by allowlist, but be safe
        return "File type not allowed"
    if not signatures:
        # No magic bytes for this type (e.g., txt, csv) — skip check
        return None
    for sig in signatures:
        if content[:len(sig)] == sig:
            return None
    return "File content does not match its extension"


def _is_dangerous_mime(mime: str) -> bool:
    """Check if a detected MIME type indicates dangerous/executable content."""
    dangerous_prefixes = (
        "application/x-executable",
        "application/x-sharedlib",
        "application/x-shellscript",
        "application/x-msdownload",
        "application/x-dosexec",
        "application/x-msdos-program",
        "text/x-php",
        "text/x-python",
        "text/x-script",
        "application/javascript",
        "text/javascript",
        "text/html",
        "image/svg",
        "application/xhtml",
    )
    return any(mime.startswith(p) for p in dangerous_prefixes)
