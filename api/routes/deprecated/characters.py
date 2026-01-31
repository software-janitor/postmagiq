"""API routes for character and outfit management."""

from __future__ import annotations

import json
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlmodel import select

from api.auth.dependencies import CurrentUser, get_current_user
from runner.content.ids import coerce_uuid, normalize_user_id
from runner.db.engine import get_session
from runner.db.models import (
    CharacterTemplate,
    OutfitPart,
    Outfit,
    OutfitItem,
    Character,
    CharacterOutfit,
    Sentiment,
    PropCategory,
)
from api.services.image_vision_service import image_vision_service

router = APIRouter(prefix="/characters", tags=["characters"])

LEGACY_META_KEY = "legacy"


# =========================================================================
# Request/Response Models
# =========================================================================


class CreateCharacterRequest(BaseModel):
    name: str
    template_id: Optional[str] = None
    description: Optional[str] = None
    skin_tone: Optional[str] = None
    face_shape: Optional[str] = None
    eye_details: Optional[str] = None
    hair_details: Optional[str] = None
    facial_hair: Optional[str] = None
    distinguishing_features: Optional[str] = None
    physical_traits: Optional[str] = None
    clothing_rules: Optional[str] = None
    visible_parts: Optional[str] = None


class UpdateCharacterRequest(BaseModel):
    name: Optional[str] = None
    template_id: Optional[str] = None
    description: Optional[str] = None
    skin_tone: Optional[str] = None
    face_shape: Optional[str] = None
    eye_details: Optional[str] = None
    hair_details: Optional[str] = None
    facial_hair: Optional[str] = None
    distinguishing_features: Optional[str] = None
    physical_traits: Optional[str] = None
    clothing_rules: Optional[str] = None
    visible_parts: Optional[str] = None


class CreateOutfitPartRequest(BaseModel):
    part_type: str
    name: str
    description: Optional[str] = None


class UpdateOutfitPartRequest(BaseModel):
    part_type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class CreateOutfitRequest(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None


class UpdateOutfitRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[str] = None


class LinkOutfitRequest(BaseModel):
    outfit_id: str
    is_default: bool = False


class CreateSentimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color_hint: Optional[str] = None
    robot_color: Optional[str] = None
    robot_eyes: Optional[str] = None
    robot_posture: Optional[str] = None


class UpdateSentimentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color_hint: Optional[str] = None
    robot_color: Optional[str] = None
    robot_eyes: Optional[str] = None
    robot_posture: Optional[str] = None


class CreatePropCategoryRequest(BaseModel):
    name: str
    description: Optional[str] = None
    context: str = "all"


class UpdatePropCategoryRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    context: Optional[str] = None


class GenerateOutfitRequest(BaseModel):
    template_type: str = "human_male"
    style: str = "professional"
    mood: Optional[str] = None
    count: int = 3
    # Style-consistent generation
    reference_outfit_ids: list[str] = []  # Outfits to use as style reference
    parts_to_vary: list[str] = []  # Which parts to generate (empty = all)
    keep_parts: dict[str, str] = {}  # part_type -> description to keep unchanged


class SuggestPartRequest(BaseModel):
    part_type: str
    style_hints: str = ""
    existing_parts: list[str] = []


def _resolve_user_id(user_id: str) -> UUID:
    """Normalize user IDs for SQLModel operations."""
    uid = normalize_user_id(user_id)
    if not uid:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    return uid


def _encode_legacy(description: Optional[str], extra: dict) -> str:
    """Encode legacy fields into a JSON description."""
    payload = {"description": description}
    payload.update(extra)
    return json.dumps({LEGACY_META_KEY: payload})


def _decode_legacy(description: Optional[str]) -> dict:
    """Decode legacy fields from a JSON description."""
    if not description:
        return {"description": None}
    try:
        payload = json.loads(description)
    except json.JSONDecodeError:
        return {"description": description}
    legacy = payload.get(LEGACY_META_KEY) if isinstance(payload, dict) else None
    if isinstance(legacy, dict):
        return legacy
    return {"description": description}


def _decode_template(record: CharacterTemplate) -> dict:
    """Map template record to legacy response shape."""
    description = record.description
    default_parts = None
    if record.base_appearance:
        try:
            parsed = json.loads(record.base_appearance)
            if isinstance(parsed, dict) and "default_parts" in parsed:
                default_parts = json.dumps(parsed["default_parts"])
            elif isinstance(parsed, list):
                default_parts = json.dumps(parsed)
            else:
                default_parts = record.base_appearance
        except json.JSONDecodeError:
            default_parts = record.base_appearance
    return {
        "id": str(record.id),
        "name": record.name,
        "description": description,
        "default_parts": default_parts,
    }


def _decode_character(record: Character) -> dict:
    """Map character record to legacy response shape."""
    legacy = _decode_legacy(record.description)
    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "name": record.name,
        "template_id": str(record.template_id) if record.template_id else None,
        "description": legacy.get("description"),
        "skin_tone": legacy.get("skin_tone"),
        "face_shape": legacy.get("face_shape"),
        "eye_details": legacy.get("eye_details"),
        "hair_details": legacy.get("hair_details"),
        "facial_hair": legacy.get("facial_hair"),
        "distinguishing_features": legacy.get("distinguishing_features"),
        "physical_traits": legacy.get("physical_traits"),
        "clothing_rules": legacy.get("clothing_rules"),
        "visible_parts": legacy.get("visible_parts"),
    }


def _decode_outfit(record: Outfit) -> dict:
    """Map outfit record to legacy response shape."""
    legacy = _decode_legacy(record.description)
    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "name": record.name,
        "description": legacy.get("description"),
        "template_id": legacy.get("template_id"),
    }


def _decode_outfit_part(record: OutfitPart) -> dict:
    """Map outfit part record to legacy response shape."""
    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "part_type": record.category,
        "name": record.name,
        "description": record.description,
    }


def _decode_sentiment(record: Sentiment) -> dict:
    """Map sentiment record to legacy response shape."""
    legacy = _decode_legacy(record.description)
    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "name": record.name,
        "description": legacy.get("description"),
        "color_hint": legacy.get("color_hint"),
        "robot_color": legacy.get("robot_color"),
        "robot_eyes": legacy.get("robot_eyes"),
        "robot_posture": legacy.get("robot_posture"),
        "is_system": legacy.get("is_system", False),
    }


def _decode_prop_category(record: PropCategory) -> dict:
    """Map prop category record to legacy response shape."""
    legacy = _decode_legacy(record.description)
    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "name": record.name,
        "description": legacy.get("description"),
        "context": legacy.get("context", "all"),
        "is_system": legacy.get("is_system", False),
    }


# =========================================================================
# Character Templates (read-only)
# =========================================================================


@router.get("/templates")
def list_templates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all character templates."""
    uid = current_user.user_id
    with get_session() as session:
        templates = session.exec(
            select(CharacterTemplate)
            .where(CharacterTemplate.user_id == uid)
            .order_by(CharacterTemplate.name)
        ).all()
        return {"templates": [_decode_template(t) for t in templates]}


@router.get("/templates/{template_id}")
def get_template(template_id: str):
    """Get a character template by ID."""
    tid = coerce_uuid(template_id)
    if not tid:
        raise HTTPException(status_code=400, detail="Invalid template ID")
    with get_session() as session:
        template = session.get(CharacterTemplate, tid)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return _decode_template(template)


# =========================================================================
# Characters
# =========================================================================


@router.get("/users/{user_id}")
def list_characters(user_id: str):
    """Get all characters for a user."""
    uid = _resolve_user_id(user_id)
    with get_session() as session:
        characters = session.exec(
            select(Character).where(Character.user_id == uid).order_by(Character.name)
        ).all()
        return {"characters": [_decode_character(c) for c in characters]}


@router.get("/{character_id}")
def get_character(character_id: str):
    """Get a character by ID."""
    cid = coerce_uuid(character_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid character ID")
    with get_session() as session:
        character = session.get(Character, cid)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        return _decode_character(character)


@router.post("/users/{user_id}")
def create_character(user_id: str, request: CreateCharacterRequest):
    """Create a new character."""
    uid = _resolve_user_id(user_id)
    template_id = coerce_uuid(request.template_id) if request.template_id else None
    if request.template_id and not template_id:
        raise HTTPException(status_code=400, detail="Invalid template ID")
    legacy_fields = {
        "skin_tone": request.skin_tone,
        "face_shape": request.face_shape,
        "eye_details": request.eye_details,
        "hair_details": request.hair_details,
        "facial_hair": request.facial_hair,
        "distinguishing_features": request.distinguishing_features,
        "physical_traits": request.physical_traits,
        "clothing_rules": request.clothing_rules,
        "visible_parts": request.visible_parts,
    }
    record = Character(
        user_id=uid,
        name=request.name,
        template_id=template_id,
        description=_encode_legacy(request.description, legacy_fields),
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"id": str(record.id)}


@router.put("/{character_id}")
def update_character(character_id: str, request: UpdateCharacterRequest):
    """Update a character."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    cid = coerce_uuid(character_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid character ID")
    with get_session() as session:
        record = session.get(Character, cid)
        if not record:
            raise HTTPException(status_code=404, detail="Character not found")

        legacy = _decode_legacy(record.description)
        if "description" in updates:
            legacy["description"] = updates.pop("description")

        for field in (
            "skin_tone",
            "face_shape",
            "eye_details",
            "hair_details",
            "facial_hair",
            "distinguishing_features",
            "physical_traits",
            "clothing_rules",
            "visible_parts",
        ):
            if field in updates:
                legacy[field] = updates.pop(field)

        if "name" in updates:
            record.name = updates.pop("name")
        if "template_id" in updates:
            template_id = coerce_uuid(updates.pop("template_id"))
            if not template_id:
                raise HTTPException(status_code=400, detail="Invalid template ID")
            record.template_id = template_id

        record.description = _encode_legacy(
            legacy.get("description"),
            {key: legacy.get(key) for key in legacy if key != "description"},
        )
        session.add(record)
        session.commit()
    return {"status": "updated"}


@router.delete("/{character_id}")
def delete_character(character_id: str):
    """Delete a character."""
    cid = coerce_uuid(character_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid character ID")
    with get_session() as session:
        record = session.get(Character, cid)
        if not record:
            return {"status": "deleted"}
        session.delete(record)
        session.commit()
    return {"status": "deleted"}


@router.post("/users/{user_id}/analyze-image")
async def analyze_character_image(
    user_id: str,
    template_type: str = Form("human_male"),
    file: UploadFile = File(...),
):
    """Upload and analyze an image to extract character details."""
    # Read image bytes
    image_bytes = await file.read()

    # Determine MIME type
    mime_type = file.content_type or "image/png"

    # Analyze with vision service
    result = image_vision_service.analyze_character_image(
        image_bytes=image_bytes,
        template_type=template_type,
        mime_type=mime_type,
    )

    return result.model_dump()


@router.post("/users/{user_id}/create-from-image")
async def create_character_from_image(
    user_id: str,
    name: str = Form(...),
    template_type: str = Form("human_male"),
    file: UploadFile = File(...),
):
    """Analyze an image and auto-create a character with extracted details.

    This endpoint combines image analysis and character creation into one step:
    1. Uploads and analyzes the image using Gemini Vision
    2. Extracts character details (face, physical traits, clothing rules)
    3. Creates the character in the database with all extracted fields

    Args:
        user_id: User ID
        name: Name for the new character
        template_type: Character type hint (human_male, human_female, non_human)
        file: Image file to analyze

    Returns:
        Created character with ID and extracted details
    """
    uid = _resolve_user_id(user_id)

    # Read image bytes
    image_bytes = await file.read()
    mime_type = file.content_type or "image/png"

    # Analyze with vision service
    result = image_vision_service.analyze_character_image(
        image_bytes=image_bytes,
        template_type=template_type,
        mime_type=mime_type,
    )

    # Look up template by type
    template_id = None
    with get_session() as session:
        # Try to find template matching the detected type
        template = session.exec(
            select(CharacterTemplate).where(
                CharacterTemplate.slug == result.template_type
            )
        ).first()
        if template:
            template_id = template.id

        # Build legacy fields from analysis
        face = result.face_details
        physical = result.physical_traits
        legacy_fields = {
            "skin_tone": face.skin_tone if face else None,
            "face_shape": face.face_shape if face else None,
            "eye_details": face.eye_details if face else None,
            "hair_details": face.hair_details if face else None,
            "facial_hair": face.facial_hair if face else None,
            "distinguishing_features": face.distinguishing_features if face else None,
            "physical_traits": (
                f"Body: {physical.body_type or 'average'}. "
                f"Posture: {physical.posture or 'natural'}. "
                f"Height: {physical.height_impression or 'average'}."
                if physical
                else None
            ),
            "clothing_rules": result.clothing_rules,
            "visible_parts": result.style_notes,
        }

        # Create the character
        record = Character(
            user_id=uid,
            name=name,
            template_id=template_id,
            description=_encode_legacy(result.raw_description, legacy_fields),
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        return {
            "id": str(record.id),
            "name": name,
            "template_type": result.template_type,
            "analysis": result.model_dump(),
            "character": _decode_character(record),
        }


# =========================================================================
# Character-Outfit Links
# =========================================================================


@router.get("/{character_id}/outfits")
def get_character_outfits(character_id: str):
    """Get all outfits linked to a character."""
    cid = coerce_uuid(character_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid character ID")
    with get_session() as session:
        character = session.get(Character, cid)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        links = session.exec(
            select(CharacterOutfit).where(CharacterOutfit.character_id == cid)
        ).all()
        outfits = []
        for link in links:
            outfit = session.get(Outfit, link.outfit_id)
            if outfit:
                outfits.append(
                    {
                        "link_id": str(link.id),
                        "is_default": outfit.id == character.default_outfit_id,
                        "outfit": _decode_outfit(outfit),
                    }
                )
        return {"outfits": outfits}


@router.post("/{character_id}/outfits")
def link_character_outfit(character_id: str, request: LinkOutfitRequest):
    """Link an outfit to a character."""
    cid = coerce_uuid(character_id)
    oid = coerce_uuid(request.outfit_id)
    if not cid or not oid:
        raise HTTPException(status_code=400, detail="Invalid character or outfit ID")
    with get_session() as session:
        character = session.get(Character, cid)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        link = session.exec(
            select(CharacterOutfit).where(
                CharacterOutfit.character_id == cid,
                CharacterOutfit.outfit_id == oid,
            )
        ).first()
        if not link:
            link = CharacterOutfit(character_id=cid, outfit_id=oid)
            session.add(link)
            session.commit()
            session.refresh(link)
        if request.is_default:
            character.default_outfit_id = oid
            session.add(character)
            session.commit()
        return {"id": str(link.id)}


@router.delete("/{character_id}/outfits/{outfit_id}")
def unlink_character_outfit(character_id: str, outfit_id: str):
    """Unlink an outfit from a character."""
    cid = coerce_uuid(character_id)
    oid = coerce_uuid(outfit_id)
    if not cid or not oid:
        raise HTTPException(status_code=400, detail="Invalid character or outfit ID")
    with get_session() as session:
        link = session.exec(
            select(CharacterOutfit).where(
                CharacterOutfit.character_id == cid,
                CharacterOutfit.outfit_id == oid,
            )
        ).first()
        if link:
            session.delete(link)
        character = session.get(Character, cid)
        if character and character.default_outfit_id == oid:
            character.default_outfit_id = None
            session.add(character)
        session.commit()
    return {"status": "unlinked"}


@router.post("/{character_id}/outfits/{outfit_id}/set-default")
def set_default_outfit(character_id: str, outfit_id: str):
    """Set an outfit as the default for a character."""
    cid = coerce_uuid(character_id)
    oid = coerce_uuid(outfit_id)
    if not cid or not oid:
        raise HTTPException(status_code=400, detail="Invalid character or outfit ID")
    with get_session() as session:
        character = session.get(Character, cid)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        character.default_outfit_id = oid
        session.add(character)
        session.commit()
    return {"status": "default set"}


# =========================================================================
# Outfit Parts
# =========================================================================


@router.get("/outfit-parts/users/{user_id}")
def list_outfit_parts(user_id: str, part_type: Optional[str] = None):
    """Get all outfit parts for a user."""
    uid = _resolve_user_id(user_id)
    with get_session() as session:
        statement = select(OutfitPart).where(OutfitPart.user_id == uid)
        if part_type:
            statement = statement.where(OutfitPart.category == part_type)
        parts = session.exec(statement.order_by(OutfitPart.name)).all()
        return {"parts": [_decode_outfit_part(p) for p in parts]}


@router.get("/outfit-parts/{part_id}")
def get_outfit_part(part_id: str):
    """Get an outfit part by ID."""
    pid = coerce_uuid(part_id)
    if not pid:
        raise HTTPException(status_code=400, detail="Invalid outfit part ID")
    with get_session() as session:
        part = session.get(OutfitPart, pid)
        if not part:
            raise HTTPException(status_code=404, detail="Outfit part not found")
        return _decode_outfit_part(part)


@router.post("/outfit-parts/users/{user_id}")
def create_outfit_part(user_id: str, request: CreateOutfitPartRequest):
    """Create a new outfit part."""
    uid = _resolve_user_id(user_id)
    record = OutfitPart(
        user_id=uid,
        category=request.part_type,
        name=request.name,
        description=request.description or "",
        is_active=True,
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"id": str(record.id)}


@router.put("/outfit-parts/{part_id}")
def update_outfit_part(part_id: str, request: UpdateOutfitPartRequest):
    """Update an outfit part."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    pid = coerce_uuid(part_id)
    if not pid:
        raise HTTPException(status_code=400, detail="Invalid outfit part ID")
    with get_session() as session:
        part = session.get(OutfitPart, pid)
        if not part:
            raise HTTPException(status_code=404, detail="Outfit part not found")
        if "part_type" in updates:
            part.category = updates.pop("part_type")
        for key, value in updates.items():
            if hasattr(part, key):
                setattr(part, key, value)
        session.add(part)
        session.commit()
    return {"status": "updated"}


@router.delete("/outfit-parts/{part_id}")
def delete_outfit_part(part_id: str):
    """Delete an outfit part."""
    pid = coerce_uuid(part_id)
    if not pid:
        raise HTTPException(status_code=400, detail="Invalid outfit part ID")
    with get_session() as session:
        part = session.get(OutfitPart, pid)
        if part:
            session.delete(part)
            session.commit()
    return {"status": "deleted"}


@router.post("/outfit-parts/suggest")
def suggest_outfit_part(request: SuggestPartRequest):
    """Get AI suggestions for an outfit part description."""
    suggestions = image_vision_service.suggest_outfit_description(
        part_type=request.part_type,
        style_hints=request.style_hints,
        existing_parts=request.existing_parts,
    )
    return {"suggestions": suggestions}


# =========================================================================
# Outfits (Outfit Bank)
# =========================================================================


@router.get("/outfits/users/{user_id}")
def list_outfits(user_id: str, template_id: Optional[str] = None):
    """Get all outfits for a user."""
    uid = _resolve_user_id(user_id)
    with get_session() as session:
        outfits = session.exec(
            select(Outfit).where(Outfit.user_id == uid).order_by(Outfit.name)
        ).all()
        decoded = [_decode_outfit(o) for o in outfits]
        if template_id:
            decoded = [o for o in decoded if o.get("template_id") == template_id]
        return {"outfits": decoded}


@router.get("/outfits/{outfit_id}")
def get_outfit(outfit_id: str):
    """Get an outfit by ID."""
    oid = coerce_uuid(outfit_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid outfit ID")
    with get_session() as session:
        outfit = session.get(Outfit, oid)
        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")
        return _decode_outfit(outfit)


@router.get("/outfits/{outfit_id}/with-parts")
def get_outfit_with_parts(outfit_id: str):
    """Get an outfit with all its parts."""
    oid = coerce_uuid(outfit_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid outfit ID")
    with get_session() as session:
        outfit = session.get(Outfit, oid)
        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")
        items = session.exec(
            select(OutfitItem).where(OutfitItem.outfit_id == oid)
        ).all()
        parts = []
        for item in items:
            part = session.get(OutfitPart, item.outfit_part_id)
            if part:
                parts.append(_decode_outfit_part(part))
        return {"outfit": _decode_outfit(outfit), "parts": parts}


@router.post("/outfits/users/{user_id}")
def create_outfit(user_id: str, request: CreateOutfitRequest):
    """Create a new outfit."""
    uid = _resolve_user_id(user_id)
    record = Outfit(
        user_id=uid,
        name=request.name,
        description=_encode_legacy(
            request.description, {"template_id": request.template_id}
        ),
        is_default=False,
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"id": str(record.id)}


@router.put("/outfits/{outfit_id}")
def update_outfit(outfit_id: str, request: UpdateOutfitRequest):
    """Update an outfit."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    oid = coerce_uuid(outfit_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid outfit ID")
    with get_session() as session:
        outfit = session.get(Outfit, oid)
        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")
        legacy = _decode_legacy(outfit.description)
        if "description" in updates:
            legacy["description"] = updates.pop("description")
        if "template_id" in updates:
            legacy["template_id"] = updates.pop("template_id")
        if "name" in updates:
            outfit.name = updates.pop("name")
        outfit.description = _encode_legacy(
            legacy.get("description"), {"template_id": legacy.get("template_id")}
        )
        session.add(outfit)
        session.commit()
    return {"status": "updated"}


@router.delete("/outfits/{outfit_id}")
def delete_outfit(outfit_id: str):
    """Delete an outfit."""
    oid = coerce_uuid(outfit_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid outfit ID")
    with get_session() as session:
        outfit = session.get(Outfit, oid)
        if outfit:
            session.delete(outfit)
            session.commit()
    return {"status": "deleted"}


@router.post("/outfits/{outfit_id}/parts/{part_id}")
def add_part_to_outfit(outfit_id: str, part_id: str):
    """Add a part to an outfit."""
    oid = coerce_uuid(outfit_id)
    pid = coerce_uuid(part_id)
    if not oid or not pid:
        raise HTTPException(status_code=400, detail="Invalid outfit or part ID")
    with get_session() as session:
        existing = session.exec(
            select(OutfitItem).where(
                OutfitItem.outfit_id == oid,
                OutfitItem.outfit_part_id == pid,
            )
        ).first()
        if existing:
            return {"id": str(existing.id)}
        record = OutfitItem(outfit_id=oid, outfit_part_id=pid)
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"id": str(record.id)}


@router.delete("/outfits/{outfit_id}/parts/{part_id}")
def remove_part_from_outfit(outfit_id: str, part_id: str):
    """Remove a part from an outfit."""
    oid = coerce_uuid(outfit_id)
    pid = coerce_uuid(part_id)
    if not oid or not pid:
        raise HTTPException(status_code=400, detail="Invalid outfit or part ID")
    with get_session() as session:
        item = session.exec(
            select(OutfitItem).where(
                OutfitItem.outfit_id == oid,
                OutfitItem.outfit_part_id == pid,
            )
        ).first()
        if item:
            session.delete(item)
            session.commit()
    return {"status": "removed"}


@router.post("/outfits/generate")
def generate_outfits(request: GenerateOutfitRequest):
    """Generate outfit suggestions using AI."""
    # Fetch reference outfit details if provided
    reference_outfits = []
    with get_session() as session:
        for outfit_id in request.reference_outfit_ids:
            oid = coerce_uuid(outfit_id)
            if not oid:
                continue
            outfit = session.get(Outfit, oid)
            if not outfit:
                continue
            items = session.exec(
                select(OutfitItem).where(OutfitItem.outfit_id == oid)
            ).all()
            parts = {}
            for item in items:
                part = session.get(OutfitPart, item.outfit_part_id)
                if part:
                    parts[part.category] = part.description
            reference_outfits.append(
                {
                    "name": outfit.name,
                    "description": _decode_legacy(outfit.description).get(
                        "description"
                    ),
                    "parts": parts,
                }
            )

    outfits = image_vision_service.generate_outfit(
        template_type=request.template_type,
        style=request.style,
        mood=request.mood,
        count=request.count,
        reference_outfits=reference_outfits,
        parts_to_vary=request.parts_to_vary,
        keep_parts=request.keep_parts,
    )
    return {"outfits": outfits}


# =========================================================================
# Sentiments
# =========================================================================


@router.get("/sentiments/users/{user_id}")
def list_sentiments(user_id: str):
    """Get all sentiments for a user (including system sentiments)."""
    uid = _resolve_user_id(user_id)
    with get_session() as session:
        sentiments = session.exec(
            select(Sentiment).where(Sentiment.user_id == uid).order_by(Sentiment.name)
        ).all()
        return {"sentiments": [_decode_sentiment(s) for s in sentiments]}


@router.get("/sentiments/{sentiment_id}")
def get_sentiment(sentiment_id: str):
    """Get a sentiment by ID."""
    sid = coerce_uuid(sentiment_id)
    if not sid:
        raise HTTPException(status_code=400, detail="Invalid sentiment ID")
    with get_session() as session:
        sentiment = session.get(Sentiment, sid)
        if not sentiment:
            raise HTTPException(status_code=404, detail="Sentiment not found")
        return _decode_sentiment(sentiment)


@router.post("/sentiments/users/{user_id}")
def create_sentiment(user_id: str, request: CreateSentimentRequest):
    """Create a new custom sentiment."""
    uid = _resolve_user_id(user_id)
    record = Sentiment(
        user_id=uid,
        name=request.name,
        description=_encode_legacy(
            request.description,
            {
                "color_hint": request.color_hint,
                "robot_color": request.robot_color,
                "robot_eyes": request.robot_eyes,
                "robot_posture": request.robot_posture,
                "is_system": False,
            },
        ),
        color_code=request.color_hint,
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"id": str(record.id)}


@router.put("/sentiments/{sentiment_id}")
def update_sentiment(sentiment_id: str, request: UpdateSentimentRequest):
    """Update a sentiment (only custom sentiments can be updated)."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    sid = coerce_uuid(sentiment_id)
    if not sid:
        raise HTTPException(status_code=400, detail="Invalid sentiment ID")
    with get_session() as session:
        sentiment = session.get(Sentiment, sid)
        if not sentiment:
            raise HTTPException(status_code=404, detail="Sentiment not found")
        legacy = _decode_legacy(sentiment.description)
        if "description" in updates:
            legacy["description"] = updates.pop("description")
        for field in ("color_hint", "robot_color", "robot_eyes", "robot_posture"):
            if field in updates:
                legacy[field] = updates.pop(field)
        if "name" in updates:
            sentiment.name = updates.pop("name")
        sentiment.description = _encode_legacy(
            legacy.get("description"),
            {
                "color_hint": legacy.get("color_hint"),
                "robot_color": legacy.get("robot_color"),
                "robot_eyes": legacy.get("robot_eyes"),
                "robot_posture": legacy.get("robot_posture"),
                "is_system": legacy.get("is_system", False),
            },
        )
        sentiment.color_code = legacy.get("color_hint")
        session.add(sentiment)
        session.commit()
    return {"status": "updated"}


@router.delete("/sentiments/{sentiment_id}")
def delete_sentiment(sentiment_id: str):
    """Delete a sentiment (only custom sentiments can be deleted)."""
    sid = coerce_uuid(sentiment_id)
    if not sid:
        raise HTTPException(status_code=400, detail="Invalid sentiment ID")
    with get_session() as session:
        sentiment = session.get(Sentiment, sid)
        if sentiment:
            session.delete(sentiment)
            session.commit()
    return {"status": "deleted"}


# =========================================================================
# Prop Categories
# =========================================================================


@router.get("/prop-categories/users/{user_id}")
def list_prop_categories(user_id: str):
    """Get all prop categories for a user (including system categories)."""
    uid = _resolve_user_id(user_id)
    with get_session() as session:
        categories = session.exec(
            select(PropCategory)
            .where(PropCategory.user_id == uid)
            .order_by(PropCategory.name)
        ).all()
        return {"categories": [_decode_prop_category(c) for c in categories]}


@router.get("/prop-categories/{category_id}")
def get_prop_category(category_id: str):
    """Get a prop category by ID."""
    cid = coerce_uuid(category_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid prop category ID")
    with get_session() as session:
        category = session.get(PropCategory, cid)
        if not category:
            raise HTTPException(status_code=404, detail="Prop category not found")
        return _decode_prop_category(category)


@router.post("/prop-categories/users/{user_id}")
def create_prop_category(user_id: str, request: CreatePropCategoryRequest):
    """Create a new custom prop category."""
    uid = _resolve_user_id(user_id)
    record = PropCategory(
        user_id=uid,
        name=request.name,
        description=_encode_legacy(
            request.description,
            {"context": request.context, "is_system": False},
        ),
    )
    with get_session() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return {"id": str(record.id)}


@router.put("/prop-categories/{category_id}")
def update_prop_category(category_id: str, request: UpdatePropCategoryRequest):
    """Update a prop category (only custom categories can be updated)."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    cid = coerce_uuid(category_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid prop category ID")
    with get_session() as session:
        category = session.get(PropCategory, cid)
        if not category:
            raise HTTPException(status_code=404, detail="Prop category not found")
        legacy = _decode_legacy(category.description)
        if "description" in updates:
            legacy["description"] = updates.pop("description")
        if "context" in updates:
            legacy["context"] = updates.pop("context")
        if "name" in updates:
            category.name = updates.pop("name")
        category.description = _encode_legacy(
            legacy.get("description"),
            {
                "context": legacy.get("context", "all"),
                "is_system": legacy.get("is_system", False),
            },
        )
        session.add(category)
        session.commit()
    return {"status": "updated"}


@router.delete("/prop-categories/{category_id}")
def delete_prop_category(category_id: str):
    """Delete a prop category (only custom categories can be deleted)."""
    cid = coerce_uuid(category_id)
    if not cid:
        raise HTTPException(status_code=400, detail="Invalid prop category ID")
    with get_session() as session:
        category = session.get(PropCategory, cid)
        if category:
            session.delete(category)
            session.commit()
    return {"status": "deleted"}
