"""
Reasoner - File Upload Module
Handles file uploads and text extraction from PDF, TXT, DOCX files.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available - PDF extraction disabled")

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available - DOCX extraction disabled")

# Upload storage directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def _get_file_extension(filename: str) -> str:
    """Get the file extension from filename."""
    return Path(filename).suffix.lower()


def _is_allowed_file(filename: str) -> bool:
    """Check if file type is allowed."""
    return _get_file_extension(filename) in SUPPORTED_EXTENSIONS


def _extract_txt(content: bytes) -> str:
    """Extract text from plain text file."""
    return content.decode("utf-8", errors="replace")


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF file."""
    if not PDF_AVAILABLE:
        return "[PDF extraction not available - install PyPDF2]"
    
    try:
        import io
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"[PDF extraction failed: {e}]"


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX file."""
    if not DOCX_AVAILABLE:
        return "[DOCX extraction not available - install python-docx]"
    
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(content))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return f"[DOCX extraction failed: {e}]"


def extract_text(content: bytes, filename: str) -> str:
    """
    Extract text content from a file based on its extension.
    
    Args:
        content: Raw file content bytes
        filename: Original filename to determine file type
        
    Returns:
        Extracted text content
    """
    ext = _get_file_extension(filename)
    
    match ext:
        case ".txt":
            return _extract_txt(content)
        case ".pdf":
            return _extract_pdf(content)
        case ".docx":
            return _extract_docx(content)
        case _:
            return f"[Unsupported file type: {ext}]"


async def save_uploaded_file(content: bytes, filename: str) -> dict[str, Any]:
    """
    Save an uploaded file and extract its text content.

    Args:
        content: Raw file content bytes
        filename: Original filename

    Returns:
        Dictionary with file info and extracted text
    """
    # Validate file type
    if not _is_allowed_file(filename):
        return {
            "success": False,
            "error": f"File type not allowed. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        }

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        return {
            "success": False,
            "error": f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
        }

    # Generate unique ID and create safe filename
    # FIX BUG-008: Prevent path traversal by using only the extension, not the full filename
    file_id = str(uuid.uuid4())[:12]
    ext = _get_file_extension(filename)
    
    # CRITICAL: Sanitize extension to prevent path traversal attacks
    # Only allow the last path component and validate it's a simple extension
    if not ext or not re.match(r'^\.[a-zA-Z0-9]+$', ext):
        return {
            "success": False,
            "error": "Invalid file extension",
        }
    
    # Safe filename: only UUID + validated extension
    safe_filename = f"{file_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    # CRITICAL: Verify the resolved path is within UPLOAD_DIR (defense in depth)
    try:
        resolved_path = file_path.resolve()
        resolved_upload_dir = UPLOAD_DIR.resolve()
        if not str(resolved_path).startswith(str(resolved_upload_dir)):
            logger.error(f"Path traversal attempt detected: {filename} -> {file_path}")
            return {
                "success": False,
                "error": "Invalid filename",
            }
    except (OSError, ValueError):
        return {
            "success": False,
            "error": "Invalid filename",
        }

    try:
        # Save file
        file_path.write_bytes(content)

        # Extract text
        text_content = extract_text(content, filename)

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "size": len(content),
            "text": text_content,
            "path": str(file_path),
        }

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_file_text(file_id: str) -> Optional[str]:
    """
    Retrieve extracted text from a previously uploaded file.
    
    Args:
        file_id: The file ID returned from save_uploaded_file
        
    Returns:
        Extracted text content or None if not found
    """
    # Find file by ID prefix
    for f in UPLOAD_DIR.glob(f"{file_id}*"):
        try:
            content = f.read_bytes()
            filename = f.name[len(file_id):]  # Remove ID prefix to get original name
            return extract_text(content, filename)
        except Exception as e:
            logger.error(f"Failed to retrieve file {file_id}: {e}")
            return None
    return None


def delete_file(file_id: str) -> bool:
    """
    Delete an uploaded file.
    
    Args:
        file_id: The file ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    for f in UPLOAD_DIR.glob(f"{file_id}*"):
        try:
            f.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
    return False


def list_uploads() -> list[dict[str, Any]]:
    """
    List all uploaded files.
    
    Returns:
        List of file info dictionaries
    """
    files = []
    for f in UPLOAD_DIR.iterdir():
        if f.is_file():
            stat = f.stat()
            files.append({
                "file_id": f.stem[:12],
                "filename": f.name[12:],  # Remove ID prefix
                "size": stat.st_size,
                "created": stat.st_ctime,
            })
    return sorted(files, key=lambda x: x["created"], reverse=True)