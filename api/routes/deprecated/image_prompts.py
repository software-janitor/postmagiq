"""API routes for image prompt generation."""

import base64
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel

from api.auth.dependencies import CurrentUser, get_current_user
from api.services.image_prompt_service import ImagePromptService
from api.services.watermark_service import WatermarkService
from runner.content.models import ImagePromptResponse

router = APIRouter(prefix="/image-prompts", tags=["image-prompts"])
service = ImagePromptService()
watermark_service = WatermarkService()


class GeneratePromptRequest(BaseModel):
    """Request to generate an image prompt."""
    post_id: str
    title: str
    sentiment: str  # "SUCCESS", "FAILURE", "UNRESOLVED"
    context: str = "software"  # "software" or "hardware"
    scene_code: Optional[str] = None
    pose_code: Optional[str] = None
    is_field_note: bool = False


@router.post("", response_model=ImagePromptResponse)
def generate_prompt(
    request: GeneratePromptRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Generate a new image prompt for a post."""
    if request.sentiment not in ["SUCCESS", "FAILURE", "UNRESOLVED"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sentiment. Must be one of: SUCCESS, FAILURE, UNRESOLVED"
        )

    if request.context not in ["software", "hardware"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid context. Must be one of: software, hardware"
        )

    return service.generate_prompt(
        user_id=str(current_user.user_id),
        post_id=request.post_id,
        title=request.title,
        sentiment=request.sentiment,
        context=request.context,
        scene_code=request.scene_code,
        pose_code=request.pose_code,
        is_field_note=request.is_field_note,
    )


@router.get("/users/{user_id}", response_model=list[ImagePromptResponse])
def list_prompts(user_id: str, post_id: Optional[str] = None):
    """List image prompts for a user, optionally filtered by post."""
    return service.get_prompts(user_id, post_id)


@router.get("/posts/{post_id}/latest", response_model=ImagePromptResponse)
def get_latest_prompt(
    post_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get the latest image prompt for a specific post."""
    prompt = service.get_latest_prompt(str(current_user.user_id), post_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="No prompt found for this post")
    return prompt


@router.get("/users/{user_id}/posts/{post_id}/latest", response_model=ImagePromptResponse)
def get_latest_prompt_for_user(user_id: str, post_id: str):
    """Get the latest image prompt for a specific post."""
    prompt = service.get_latest_prompt(user_id, post_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="No prompt found for this post")
    return prompt


@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str):
    """Delete an image prompt."""
    service.delete_prompt(prompt_id)
    return {"status": "deleted", "id": prompt_id}


@router.get("/scenes")
def get_scenes(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all available scene options from database."""
    return {"scenes": service.get_scenes_for_user(str(current_user.user_id))}


@router.get("/poses")
def get_poses(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all available pose options from database."""
    return {"poses": service.get_poses_for_user(str(current_user.user_id))}


@router.get("/outfits")
def get_outfits(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all available outfit options from database."""
    return {"outfits": service.get_outfits_for_user(str(current_user.user_id))}


# =============================================================================
# Image Upload with Watermark Removal
# =============================================================================


class ImageUploadResponse(BaseModel):
    """Response for image upload."""
    success: bool
    post_id: Optional[str] = None
    prompt_id: Optional[str] = None
    watermark_removed: bool = False
    has_image: bool = False
    error: Optional[str] = None


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    post_id: str = Form(...),
    prompt_id: Optional[str] = Form(default=None),
    remove_watermark: bool = Form(default=True),
):
    """Upload an image for a post, remove watermark, and store in database.

    The image will be:
    1. Watermark removed using LaMA AI (if enabled)
    2. Stored as base64 in the database with the image prompt record

    Args:
        file: The image file to upload
        post_id: Post identifier (e.g., "c1p1" for chapter 1 post 1)
        prompt_id: Optional prompt ID to attach image to (uses latest if not provided)
        remove_watermark: Whether to remove watermarks (default True, uses LaMA)

    Returns:
        Upload result with prompt_id where image was stored
    """
    # Get or find the prompt to attach image to
    target_prompt_id = prompt_id
    if not target_prompt_id:
        # Find the latest prompt for this post
        uid = str(current_user.user_id)
        latest = service.get_latest_prompt(uid, post_id)
        if latest:
            target_prompt_id = latest.id
        else:
            return ImageUploadResponse(
                success=False,
                post_id=post_id,
                error="No image prompt found for this post. Generate a prompt first.",
            )

    # Determine output format from extension
    ext = Path(file.filename).suffix.lower() or ".png"
    output_format = "png"
    if ext in (".jpg", ".jpeg"):
        output_format = "jpg"
    elif ext == ".webp":
        output_format = "webp"

    try:
        # Read uploaded image bytes
        image_bytes = await file.read()

        watermark_removed = False
        image_data = None

        if remove_watermark:
            # Remove watermark using LaMA service
            result = watermark_service.remove_watermark_bytes(
                image_bytes=image_bytes,
                filename=file.filename or "image.png",
                output_format=output_format,
            )

            if result.get("success"):
                watermark_removed = True
                image_data = result["image_data"]
            else:
                # Watermark removal failed, store original
                image_data = base64.b64encode(image_bytes).decode("utf-8")
        else:
            # No watermark removal, store as-is
            image_data = base64.b64encode(image_bytes).decode("utf-8")

        # Store in database
        service.update_image(target_prompt_id, image_data)

        return ImageUploadResponse(
            success=True,
            post_id=post_id,
            prompt_id=target_prompt_id,
            watermark_removed=watermark_removed,
            has_image=True,
        )

    except Exception as e:
        return ImageUploadResponse(
            success=False,
            post_id=post_id,
            error=str(e),
        )


@router.get("/{prompt_id}/image")
def get_prompt_image(
    prompt_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get the image data for a specific prompt.

    Returns base64 encoded image data.
    """
    # Get all prompts and find the one with this ID
    prompts = service.get_prompts(str(current_user.user_id))
    prompt = next((p for p in prompts if p.id == prompt_id), None)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not prompt.image_data:
        raise HTTPException(status_code=404, detail="No image stored for this prompt")

    return {
        "prompt_id": prompt_id,
        "post_id": prompt.post_id,
        "image_data": prompt.image_data,
        "has_image": True,
    }


@router.get("/{prompt_id}/download")
def download_prompt_image(
    prompt_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Download the full resolution image for a prompt.

    Returns the image file directly for download.
    """
    # Get all prompts and find the one with this ID
    prompts = service.get_prompts(str(current_user.user_id))
    prompt = next((p for p in prompts if p.id == prompt_id), None)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not prompt.image_data:
        raise HTTPException(status_code=404, detail="No image stored for this prompt")

    # Decode base64 to bytes
    image_bytes = base64.b64decode(prompt.image_data)

    # Determine content type (assume PNG if unknown)
    content_type = "image/png"

    # Generate filename
    filename = f"{prompt.post_id}_v{prompt.version}.png"

    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/users/{user_id}/posts/{post_id}/image")
def get_post_image(user_id: str, post_id: str):
    """Get the image for a post (from the latest prompt).

    Returns base64 encoded image data.
    """
    latest = service.get_latest_prompt(user_id, post_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No prompt found for this post")

    if not latest.image_data:
        raise HTTPException(status_code=404, detail="No image stored for this post")

    return {
        "prompt_id": latest.id,
        "post_id": post_id,
        "image_data": latest.image_data,
        "has_image": True,
    }


@router.post("/{prompt_id}/remove-watermark", response_model=ImageUploadResponse)
def remove_watermark_from_existing(
    prompt_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Re-process watermark removal on an existing image.

    Use this when the LaMA service wasn't available during upload
    and you want to process the watermark removal now.
    """
    # Get the prompt with image
    prompts = service.get_prompts(str(current_user.user_id))
    prompt = next((p for p in prompts if p.id == prompt_id), None)

    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not prompt.image_data:
        raise HTTPException(status_code=404, detail="No image stored for this prompt")

    # Check if watermark service is available
    if not watermark_service.is_available().get("available"):
        return ImageUploadResponse(
            success=False,
            post_id=prompt.post_id,
            prompt_id=prompt_id,
            error="Watermark removal service is not available. Make sure LaMA is running on port 8001.",
        )

    try:
        # Decode existing image
        image_bytes = base64.b64decode(prompt.image_data)

        # Process watermark removal
        result = watermark_service.remove_watermark_bytes(
            image_bytes=image_bytes,
            filename=f"{prompt.post_id}.png",
            output_format="png",
        )

        if result.get("success"):
            # Update the image in database with watermark-removed version
            service.update_image(prompt_id, result["image_data"])
            return ImageUploadResponse(
                success=True,
                post_id=prompt.post_id,
                prompt_id=prompt_id,
                watermark_removed=True,
                has_image=True,
            )
        else:
            return ImageUploadResponse(
                success=False,
                post_id=prompt.post_id,
                prompt_id=prompt_id,
                error=result.get("error", "Watermark removal failed"),
            )

    except Exception as e:
        return ImageUploadResponse(
            success=False,
            post_id=prompt.post_id,
            prompt_id=prompt_id,
            error=str(e),
        )
