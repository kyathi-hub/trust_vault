"""
Upload validation security tests.

Tests that malicious uploads are rejected:
- Path traversal filenames
- Dangerous extensions
- MIME spoofing (exe renamed to pdf)
- Oversized files
- Null bytes in filename
- Double extensions
"""
import pytest

from app.documents.upload_validation import validate_upload

# Minimal valid PDF magic bytes
VALID_PDF_BYTES = b"%PDF-1.4 fake pdf content for testing"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
EXE_BYTES = b"MZ" + b"\x00" * 100  # Windows PE header


def test_valid_pdf_accepted() -> None:
    result = validate_upload("document.pdf", VALID_PDF_BYTES, "application/pdf")
    assert result.ok


def test_valid_png_accepted() -> None:
    result = validate_upload("image.png", VALID_PNG_BYTES, "image/png")
    assert result.ok


def test_path_traversal_rejected() -> None:
    result = validate_upload("../../../etc/passwd", VALID_PDF_BYTES, "application/pdf")
    assert not result.ok


def test_path_traversal_windows_rejected() -> None:
    result = validate_upload("..\\..\\windows\\system32\\file.pdf", VALID_PDF_BYTES, "application/pdf")
    assert not result.ok


def test_null_byte_filename_rejected() -> None:
    result = validate_upload("file\x00.pdf", VALID_PDF_BYTES, "application/pdf")
    assert not result.ok


def test_exe_extension_rejected() -> None:
    result = validate_upload("malware.exe", EXE_BYTES, "application/octet-stream")
    assert not result.ok


def test_bat_extension_rejected() -> None:
    result = validate_upload("script.bat", b"@echo off", "text/plain")
    assert not result.ok


def test_double_extension_rejected() -> None:
    """evil.pdf.exe must be rejected."""
    result = validate_upload("evil.pdf.exe", EXE_BYTES, "application/pdf")
    assert not result.ok


def test_mime_spoofing_exe_as_pdf() -> None:
    """EXE file renamed to .pdf — magic bytes won't match PDF signature."""
    result = validate_upload("malware.pdf", EXE_BYTES, "application/pdf")
    assert not result.ok


def test_oversized_file_rejected() -> None:
    huge_content = b"A" * (60 * 1024 * 1024)  # 60MB > 50MB limit
    result = validate_upload("big.pdf", huge_content, "application/pdf")
    assert not result.ok


def test_html_extension_rejected() -> None:
    result = validate_upload("page.html", b"<html>xss</html>", "text/html")
    assert not result.ok


def test_svg_extension_rejected() -> None:
    result = validate_upload("image.svg", b"<svg><script>alert(1)</script></svg>", "image/svg+xml")
    assert not result.ok


def test_empty_filename_rejected() -> None:
    result = validate_upload("", VALID_PDF_BYTES, "application/pdf")
    assert not result.ok


def test_checksum_computed_on_success() -> None:
    result = validate_upload("document.pdf", VALID_PDF_BYTES, "application/pdf")
    assert result.ok
    assert result.checksum_sha256 is not None
    assert len(result.checksum_sha256) == 64
