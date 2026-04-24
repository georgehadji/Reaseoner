"""File upload endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from reasoner.api.auth_deps import check_rate_limit, optional_auth
from reasoner.uploader import delete_file, get_file_text, list_uploads, save_uploaded_file, save_uploaded_files

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/upload")
async def upload_file(
    request: Request,
    force_ocr: bool = Query(False, description="Use OCR for images and scanned PDFs"),
    authenticated=Depends(optional_auth),
    rate_limit_checked=Depends(check_rate_limit),
):
    """Upload one or more files and extract their text content."""
    try:
        form = await request.form()
        files = []

        # FastAPI/Uvicorn sends multiple files with the same key as a list or single item
        raw_files = form.getlist("file") if hasattr(form, "getlist") else form.multi_items()
        if not raw_files:
            # Fallback for single file
            single = form.get("file")
            if single:
                raw_files = [single]

        if not raw_files:
            return {"success": False, "error": "No file provided"}

        # Normalize to list of (bytes, filename) tuples
        for item in raw_files:
            if hasattr(item, "read"):
                content = await item.read()
                files.append((content, getattr(item, "filename", "unknown")))

        if len(files) == 1:
            result = await save_uploaded_file(files[0][0], files[0][1], force_ocr=force_ocr)
            return {"success": True, "files": [result]}
        else:
            results = await save_uploaded_files(files, force_ocr=force_ocr)
            return {"success": True, "files": results}

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/uploads")
async def get_uploads(
    authenticated=Depends(optional_auth),
    rate_limit_checked=Depends(check_rate_limit),
):
    """List all uploaded files."""
    return {"files": list_uploads()}


@router.get("/api/upload/{file_id}")
async def get_uploaded_file(
    file_id: str,
    authenticated=Depends(optional_auth),
    rate_limit_checked=Depends(check_rate_limit),
):
    """Get text content of an uploaded file."""
    text = await get_file_text(file_id)
    if text is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_id": file_id, "text": text}


@router.delete("/api/upload/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    authenticated=Depends(optional_auth),
    rate_limit_checked=Depends(check_rate_limit),
):
    """Delete an uploaded file."""
    success = delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "deleted"}
