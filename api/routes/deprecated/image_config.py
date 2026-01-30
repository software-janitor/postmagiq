"""API routes for image prompt configuration."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.image_config_service import ImageConfigService
from api.services.scene_generator_service import scene_generator_service

router = APIRouter(prefix="/image-config", tags=["image-config"])
service = ImageConfigService()


# Request models
class CreateSceneRequest(BaseModel):
    code: str
    name: str
    sentiment: str
    description: str
    viewpoint: str = "standard"
    is_hardware_only: bool = False
    no_desk_props: bool = False


class UpdateSceneRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    viewpoint: Optional[str] = None
    is_hardware_only: Optional[bool] = None
    no_desk_props: Optional[bool] = None


class CreatePoseRequest(BaseModel):
    code: str
    sentiment: str
    description: str
    emotional_note: Optional[str] = None


class UpdatePoseRequest(BaseModel):
    description: Optional[str] = None
    emotional_note: Optional[str] = None


class CreateOutfitRequest(BaseModel):
    vest: str
    shirt: str
    pants: str = "Dark pants"


class UpdateOutfitRequest(BaseModel):
    vest: Optional[str] = None
    shirt: Optional[str] = None
    pants: Optional[str] = None


class CreatePropRequest(BaseModel):
    category: str
    description: str
    context: str = "all"


class UpdatePropRequest(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    context: Optional[str] = None


class UpdateCharacterRequest(BaseModel):
    appearance: Optional[str] = None
    face_details: Optional[str] = None
    clothing_rules: Optional[str] = None


class CreateConfigSetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False


class UpdateConfigSetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CloneConfigSetRequest(BaseModel):
    new_name: str


class AddSceneCharacterRequest(BaseModel):
    character_id: str
    outfit_id: Optional[str] = None
    position: Optional[str] = None


class UpdateSceneCharacterRequest(BaseModel):
    outfit_id: Optional[str] = None
    position: Optional[str] = None


class GenerateScenesRequest(BaseModel):
    sentiment: str
    count: int = 5
    themes: Optional[list[str]] = None
    context: str = "software"


class GenerateVariationsRequest(BaseModel):
    count: int = 3
    vary: Optional[list[str]] = None


class PreviewSceneRequest(BaseModel):
    scene: dict
    characters: Optional[list[dict]] = None
    outfit_override: Optional[dict] = None


# =========================================================================
# Seed/Initialize
# =========================================================================


@router.post("/users/{user_id}/seed")
def seed_defaults(user_id: str):
    """Seed default configurations for a user."""
    result = service.seed_defaults(user_id)
    return result


@router.post("/users/{user_id}/reset")
def reset_defaults(user_id: str):
    """Delete all config and re-seed with defaults."""
    result = service.reset_defaults(user_id)
    return result


# =========================================================================
# Scenes
# =========================================================================


@router.get("/users/{user_id}/scenes")
def list_scenes(user_id: str, sentiment: Optional[str] = None):
    """List all scenes for a user."""
    scenes = service.get_scenes(user_id, sentiment)
    return {"scenes": scenes}


@router.get("/scenes/{scene_id}")
def get_scene(scene_id: str):
    """Get a single scene."""
    scene = service.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.post("/users/{user_id}/scenes")
def create_scene(user_id: str, request: CreateSceneRequest):
    """Create a new scene."""
    scene_id = service.create_scene(
        user_id=user_id,
        code=request.code,
        name=request.name,
        sentiment=request.sentiment,
        description=request.description,
        viewpoint=request.viewpoint,
        is_hardware_only=request.is_hardware_only,
        no_desk_props=request.no_desk_props,
    )
    return {"id": scene_id}


@router.put("/scenes/{scene_id}")
def update_scene(scene_id: str, request: UpdateSceneRequest):
    """Update a scene."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_scene(scene_id, **updates)
    return {"status": "updated"}


@router.delete("/scenes/{scene_id}")
def delete_scene(scene_id: str):
    """Delete a scene."""
    service.delete_scene(scene_id)
    return {"status": "deleted"}


# =========================================================================
# Poses
# =========================================================================


@router.get("/users/{user_id}/poses")
def list_poses(user_id: str, sentiment: Optional[str] = None):
    """List all poses for a user."""
    poses = service.get_poses(user_id, sentiment)
    return {"poses": poses}


@router.post("/users/{user_id}/poses")
def create_pose(user_id: str, request: CreatePoseRequest):
    """Create a new pose."""
    pose_id = service.create_pose(
        user_id=user_id,
        code=request.code,
        sentiment=request.sentiment,
        description=request.description,
        emotional_note=request.emotional_note,
    )
    return {"id": pose_id}


@router.put("/poses/{pose_id}")
def update_pose(pose_id: str, request: UpdatePoseRequest):
    """Update a pose."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_pose(pose_id, **updates)
    return {"status": "updated"}


@router.delete("/poses/{pose_id}")
def delete_pose(pose_id: str):
    """Delete a pose."""
    service.delete_pose(pose_id)
    return {"status": "deleted"}


# =========================================================================
# Outfits
# =========================================================================


@router.get("/users/{user_id}/outfits")
def list_outfits(user_id: str):
    """List all outfits for a user."""
    outfits = service.get_outfits(user_id)
    return {"outfits": outfits}


@router.post("/users/{user_id}/outfits")
def create_outfit(user_id: str, request: CreateOutfitRequest):
    """Create a new outfit."""
    outfit_id = service.create_outfit(
        user_id=user_id,
        vest=request.vest,
        shirt=request.shirt,
        pants=request.pants,
    )
    return {"id": outfit_id}


@router.put("/outfits/{outfit_id}")
def update_outfit(outfit_id: str, request: UpdateOutfitRequest):
    """Update an outfit."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_outfit(outfit_id, **updates)
    return {"status": "updated"}


@router.delete("/outfits/{outfit_id}")
def delete_outfit(outfit_id: str):
    """Delete an outfit."""
    service.delete_outfit(outfit_id)
    return {"status": "deleted"}


class BulkOutfitImportRequest(BaseModel):
    """Request for bulk outfit import."""

    outfits: list[CreateOutfitRequest]


class BulkImportResponse(BaseModel):
    """Response for bulk import operations."""

    imported: int
    skipped: int
    errors: list[str]


@router.post("/users/{user_id}/outfits/bulk", response_model=BulkImportResponse)
def bulk_import_outfits(user_id: str, request: BulkOutfitImportRequest):
    """Bulk import outfits from JSON array.

    Accepts an array of outfit objects: [{"vest": "...", "shirt": "...", "pants": "..."}]

    - Duplicates are skipped (case-insensitive match on vest+shirt+pants)
    - Pants defaults to "Dark pants" if not specified
    """
    outfits_data = [o.model_dump() for o in request.outfits]
    result = service.bulk_import_outfits(user_id, outfits_data)
    return BulkImportResponse(**result)


# =========================================================================
# Props
# =========================================================================


@router.get("/users/{user_id}/props")
def list_props(user_id: str, category: Optional[str] = None):
    """List all props for a user."""
    props = service.get_props(user_id, category)
    return {"props": props}


@router.post("/users/{user_id}/props")
def create_prop(user_id: str, request: CreatePropRequest):
    """Create a new prop."""
    prop_id = service.create_prop(
        user_id=user_id,
        category=request.category,
        description=request.description,
        context=request.context,
    )
    return {"id": prop_id}


@router.put("/props/{prop_id}")
def update_prop(prop_id: str, request: UpdatePropRequest):
    """Update a prop."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_prop(prop_id, **updates)
    return {"status": "updated"}


@router.delete("/props/{prop_id}")
def delete_prop(prop_id: str):
    """Delete a prop."""
    service.delete_prop(prop_id)
    return {"status": "deleted"}


# =========================================================================
# Characters
# =========================================================================


@router.get("/users/{user_id}/characters")
def list_characters(user_id: str):
    """List all character definitions for a user."""
    characters = service.get_characters(user_id)
    return {"characters": characters}


@router.get("/users/{user_id}/characters/{character_type}")
def get_character(user_id: str, character_type: str):
    """Get a specific character definition."""
    character = service.get_character(user_id, character_type)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.put("/characters/{character_id}")
def update_character(character_id: str, request: UpdateCharacterRequest):
    """Update a character."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_character(character_id, **updates)
    return {"status": "updated"}


# =========================================================================
# Config Sets
# =========================================================================


@router.get("/users/{user_id}/config-sets")
def list_config_sets(user_id: str):
    """List all image config sets for a user."""
    config_sets = service.get_config_sets(user_id)
    return {"config_sets": config_sets}


@router.get("/config-sets/{config_set_id}")
def get_config_set(config_set_id: str):
    """Get a single config set."""
    config_set = service.get_config_set(config_set_id)
    if not config_set:
        raise HTTPException(status_code=404, detail="Config set not found")
    return config_set


@router.post("/users/{user_id}/config-sets")
def create_config_set(user_id: str, request: CreateConfigSetRequest):
    """Create a new config set."""
    config_set_id = service.create_config_set(
        user_id=user_id,
        name=request.name,
        description=request.description,
        is_default=request.is_default,
    )
    return {"id": config_set_id}


@router.put("/config-sets/{config_set_id}")
def update_config_set(config_set_id: str, request: UpdateConfigSetRequest):
    """Update a config set."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_config_set(config_set_id, **updates)
    return {"status": "updated"}


@router.post("/config-sets/{config_set_id}/set-default")
def set_default_config_set(config_set_id: str, user_id: str):
    """Set a config set as the default."""
    service.set_default_config_set(user_id, config_set_id)
    return {"status": "default set"}


@router.post("/config-sets/{config_set_id}/clone")
def clone_config_set(config_set_id: str, request: CloneConfigSetRequest):
    """Clone a config set with a new name."""
    new_id = service.clone_config_set(config_set_id, request.new_name)
    return {"id": new_id}


@router.delete("/config-sets/{config_set_id}")
def delete_config_set(config_set_id: str):
    """Delete a config set."""
    service.delete_config_set(config_set_id)
    return {"status": "deleted"}


# =========================================================================
# Scene-Character Integration
# =========================================================================


@router.get("/scenes/{scene_id}/characters")
def get_scene_characters(scene_id: str):
    """Get all characters linked to a scene."""
    characters = service.get_scene_characters(scene_id)
    return {"characters": characters}


@router.post("/scenes/{scene_id}/characters")
def add_scene_character(scene_id: str, request: AddSceneCharacterRequest):
    """Add a character to a scene."""
    link_id = service.add_scene_character(
        scene_id=scene_id,
        character_id=request.character_id,
        outfit_id=request.outfit_id,
        position=request.position,
    )
    return {"id": link_id}


@router.put("/scenes/{scene_id}/characters/{character_id}")
def update_scene_character(
    scene_id: str, character_id: str, request: UpdateSceneCharacterRequest
):
    """Update a character's outfit or position in a scene."""
    service.update_scene_character(
        scene_id=scene_id,
        character_id=character_id,
        outfit_id=request.outfit_id,
        position=request.position,
    )
    return {"status": "updated"}


@router.delete("/scenes/{scene_id}/characters/{character_id}")
def remove_scene_character(scene_id: str, character_id: str):
    """Remove a character from a scene."""
    service.remove_scene_character(scene_id, character_id)
    return {"status": "removed"}


# =========================================================================
# Scene Generation (AI)
# =========================================================================


@router.post("/scenes/generate")
def generate_scenes(request: GenerateScenesRequest):
    """Generate scene descriptions using AI."""
    scenes = scene_generator_service.generate_scenes(
        sentiment=request.sentiment,
        count=request.count,
        themes=request.themes,
        context=request.context,
    )
    return {"scenes": scenes}


@router.post("/scenes/{scene_id}/variations")
def generate_scene_variations(scene_id: str, request: GenerateVariationsRequest):
    """Generate variations of an existing scene."""
    # Get the original scene
    scene = service.get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    variations = scene_generator_service.generate_scene_variations(
        original_scene=scene,
        count=request.count,
        vary=request.vary,
    )
    return {"variations": variations}


@router.post("/scenes/preview")
def preview_scene_prompt(request: PreviewSceneRequest):
    """Generate a preview of the full image prompt for a scene."""
    preview = scene_generator_service.preview_scene_prompt(
        scene=request.scene,
        characters=request.characters,
        outfit_override=request.outfit_override,
    )
    return {"preview": preview}


# =========================================================================
# Prop Categories
# =========================================================================


class CreatePropCategoryRequest(BaseModel):
    name: str
    description: Optional[str] = None
    context: str = "all"


class UpdatePropCategoryRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    context: Optional[str] = None


@router.get("/users/{user_id}/prop-categories")
def list_prop_categories(user_id: str):
    """List all prop categories for a user."""
    categories = service.get_prop_categories(user_id)
    return {"categories": categories}


@router.get("/prop-categories/{category_id}")
def get_prop_category(category_id: str):
    """Get a single prop category."""
    category = service.get_prop_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Prop category not found")
    return category


@router.post("/users/{user_id}/prop-categories")
def create_prop_category(user_id: str, request: CreatePropCategoryRequest):
    """Create a new prop category."""
    category_id = service.create_prop_category(
        user_id=user_id,
        name=request.name,
        description=request.description,
        context=request.context,
    )
    return {"id": category_id}


@router.put("/prop-categories/{category_id}")
def update_prop_category(category_id: str, request: UpdatePropCategoryRequest):
    """Update a prop category."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    service.update_prop_category(category_id, **updates)
    return {"status": "updated"}


@router.delete("/prop-categories/{category_id}")
def delete_prop_category(category_id: str):
    """Delete a prop category."""
    service.delete_prop_category(category_id)
    return {"status": "deleted"}


# =========================================================================
# Scene Prop Rules
# =========================================================================


class AddScenePropRuleRequest(BaseModel):
    prop_category_id: Optional[str] = None
    prop_id: Optional[str] = None
    required: bool = False
    excluded: bool = False
    max_count: int = 1


@router.get("/scenes/{scene_id}/prop-rules")
def get_scene_prop_rules(scene_id: str):
    """Get all prop rules for a scene."""
    rules = service.get_scene_prop_rules(scene_id)
    return {"rules": rules}


@router.post("/scenes/{scene_id}/prop-rules")
def add_scene_prop_rule(scene_id: str, request: AddScenePropRuleRequest):
    """Add a prop rule to a scene."""
    rule_id = service.add_scene_prop_rule(
        scene_id=scene_id,
        prop_category_id=request.prop_category_id,
        prop_id=request.prop_id,
        required=request.required,
        excluded=request.excluded,
        max_count=request.max_count,
    )
    return {"id": rule_id}


@router.delete("/prop-rules/{rule_id}")
def remove_scene_prop_rule(rule_id: str):
    """Remove a scene prop rule."""
    service.remove_scene_prop_rule(rule_id)
    return {"status": "deleted"}


# =========================================================================
# Context Prop Rules
# =========================================================================


class SetContextPropRuleRequest(BaseModel):
    context: str
    prop_category_id: str
    weight: int = 1


@router.get("/users/{user_id}/context-prop-rules")
def get_context_prop_rules(user_id: str, context: Optional[str] = None):
    """Get context-based prop rules."""
    rules = service.get_context_prop_rules(user_id, context)
    return {"rules": rules}


@router.post("/users/{user_id}/context-prop-rules")
def set_context_prop_rule(user_id: str, request: SetContextPropRuleRequest):
    """Set a context-based prop rule."""
    rule_id = service.set_context_prop_rule(
        user_id=user_id,
        context=request.context,
        prop_category_id=request.prop_category_id,
        weight=request.weight,
    )
    return {"id": rule_id}


@router.delete("/context-prop-rules/{rule_id}")
def remove_context_prop_rule(rule_id: str):
    """Remove a context prop rule."""
    service.remove_context_prop_rule(rule_id)
    return {"status": "deleted"}
