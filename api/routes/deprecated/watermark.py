"""API routes for watermark removal.

Owner-only: These are internal image processing tools.
"""

import shutil
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from api.auth.dependencies import CurrentUser, require_owner_role
from api.services.watermark_service import WatermarkService

router = APIRouter(prefix="/watermark", tags=["watermark"])
service = WatermarkService()


class RemoveWatermarkRequest(BaseModel):
    input_path: str
    output_path: Optional[str] = None
    use_lama: bool = True


class RemoveWatermarkResponse(BaseModel):
    success: bool
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    method: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status")
def get_status(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Check if watermark removal is available."""
    return service.is_available()


@router.post("/remove", response_model=RemoveWatermarkResponse)
def remove_watermark(
    request: RemoveWatermarkRequest,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
):
    """Remove watermark from an image by path.

    Uses LaMA AI inpainting by default for best quality.
    Falls back to fast math-based approach if LaMA unavailable.
    """
    result = service.remove_watermark(
        input_path=request.input_path,
        output_path=request.output_path,
        use_lama=request.use_lama,
    )
    return RemoveWatermarkResponse(**result)


@router.post("/remove-upload", response_model=RemoveWatermarkResponse)
async def remove_watermark_upload(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    file: UploadFile = File(...),
    use_lama: bool = Form(default=True),
    chapter: Optional[str] = Form(default=None),
):
    """Remove watermark from an uploaded image.

    Args:
        file: The image file to process
        use_lama: Use LaMA AI inpainting (default True)
        chapter: Optional chapter identifier (e.g., "c1p1") for organizing output

    Returns:
        Path to the cleaned image
    """
    # Create temp directory for uploads
    upload_dir = Path("workflow/watermark_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Determine output location
    if chapter:
        output_dir = Path(f"images/chapter_{chapter}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"{chapter}_clean{Path(file.filename).suffix}"
        output_path = output_dir / output_filename
    else:
        output_path = None  # Will use default naming

    # Save uploaded file
    input_path = upload_dir / file.filename
    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Process watermark removal
        result = service.remove_watermark(
            input_path=str(input_path),
            output_path=str(output_path) if output_path else None,
            use_lama=use_lama,
        )

        return RemoveWatermarkResponse(**result)

    finally:
        # Clean up uploaded file
        if input_path.exists():
            input_path.unlink()


@router.post("/remove-batch")
def remove_watermark_batch(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
    input_dir: str = Form(...),
    output_dir: Optional[str] = Form(default=None),
    use_lama: bool = Form(default=True),
):
    """Remove watermarks from all images in a directory.

    Args:
        input_dir: Directory containing images to process
        output_dir: Output directory (default: same as input)
        use_lama: Use LaMA AI inpainting (default True)
    """
    result = service.remove_watermark_batch(
        input_dir=input_dir,
        output_dir=output_dir,
        use_lama=use_lama,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
