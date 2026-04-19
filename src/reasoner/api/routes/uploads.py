"""File upload endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from reasoner.uploader import delete_file, get_file_text, list_uploads, save_uploaded_file

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/upload")
async def upload_file(request: Request):
    """Upload a file and extract its text content."""
    try:
        form = await request.form()
        file = form.get("file")
        if not file:
            return {"success": False, "error": "No file provided"}

        content = await file.read()
        result = await save_uploaded_file(content, file.filename)
        return result

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/uploads")
async def get_uploads():
    """List all uploaded files."""
    return {"files": list_uploads()}


@router.get("/api/upload/{file_id}")
async def get_uploaded_file(file_id: str):
    """Get text content of an uploaded file."""
    text = get_file_text(file_id)
    if text is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_id": file_id, "text": text}


@router.delete("/api/upload/{file_id}")
async def delete_uploaded_file(file_id: str):
    """Delete an uploaded file."""
    success = delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "deleted"}
