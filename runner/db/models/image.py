"""Image models: ImagePrompt, ImageConfigSet, ImageScene, ImagePose, etc."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# ImagePrompt
# =============================================================================

class ImagePromptBase(SQLModel):
    """Base image prompt fields."""

    post_id: str = Field(index=True)
    sentiment: Optional[str] = None
    context: str = Field(default="software")
    scene_code: Optional[str] = None
    scene_name: Optional[str] = None
    pose_code: Optional[str] = None
    outfit_vest: Optional[str] = None
    outfit_shirt: Optional[str] = None
    prompt_content: str
    version: int = Field(default=1)
    image_data: Optional[str] = None  # Base64 encoded image


class ImagePrompt(UUIDModel, ImagePromptBase, TimestampMixin, table=True):
    """ImagePrompt table - generated image prompts for posts."""

    __tablename__ = "image_prompts"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImagePromptCreate(ImagePromptBase):
    """Schema for creating a new image prompt."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


class ImagePromptRead(ImagePromptBase):
    """Schema for reading image prompt data."""

    id: UUID
    user_id: UUID
    workspace_id: Optional[UUID]
    created_at: datetime


# =============================================================================
# ImageConfigSet
# =============================================================================

class ImageConfigSetBase(SQLModel):
    """Base image config set fields."""

    name: str
    description: Optional[str] = None
    is_default: bool = Field(default=False)


class ImageConfigSet(UUIDModel, ImageConfigSetBase, TimestampMixin, table=True):
    """ImageConfigSet table - groups of image configurations."""

    __tablename__ = "image_config_sets"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImageConfigSetCreate(ImageConfigSetBase):
    """Schema for creating a new image config set."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# ImageScene
# =============================================================================

class ImageSceneBase(SQLModel):
    """Base image scene fields."""

    code: str = Field(index=True)
    name: str
    sentiment: str
    viewpoint: str = Field(default="standard")
    description: str
    is_hardware_only: bool = Field(default=False)
    no_desk_props: bool = Field(default=False)


class ImageScene(UUIDModel, ImageSceneBase, TimestampMixin, table=True):
    """ImageScene table - configurable scene definitions."""

    __tablename__ = "image_scenes"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImageSceneCreate(ImageSceneBase):
    """Schema for creating a new image scene."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# ImagePose
# =============================================================================

class ImagePoseBase(SQLModel):
    """Base image pose fields."""

    code: str = Field(index=True)
    sentiment: str
    description: str
    emotional_note: Optional[str] = None


class ImagePose(UUIDModel, ImagePoseBase, TimestampMixin, table=True):
    """ImagePose table - configurable pose definitions."""

    __tablename__ = "image_poses"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImagePoseCreate(ImagePoseBase):
    """Schema for creating a new image pose."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# ImageOutfit
# =============================================================================

class ImageOutfitBase(SQLModel):
    """Base image outfit fields."""

    vest: str
    shirt: str
    pants: str = Field(default="Dark pants")


class ImageOutfit(UUIDModel, ImageOutfitBase, TimestampMixin, table=True):
    """ImageOutfit table - configurable outfit options."""

    __tablename__ = "image_outfits"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImageOutfitCreate(ImageOutfitBase):
    """Schema for creating a new image outfit."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# ImageProp
# =============================================================================

class ImagePropBase(SQLModel):
    """Base image prop fields."""

    category: str
    description: str
    context: str = Field(default="all")


class ImageProp(UUIDModel, ImagePropBase, TimestampMixin, table=True):
    """ImageProp table - configurable desk props."""

    __tablename__ = "image_props"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImagePropCreate(ImagePropBase):
    """Schema for creating a new image prop."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# ImageCharacter
# =============================================================================

class ImageCharacterBase(SQLModel):
    """Base image character fields."""

    character_type: str
    appearance: str
    face_details: Optional[str] = None
    clothing_rules: Optional[str] = None


class ImageCharacter(UUIDModel, ImageCharacterBase, TimestampMixin, table=True):
    """ImageCharacter table - character appearance definitions."""

    __tablename__ = "image_characters"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class ImageCharacterCreate(ImageCharacterBase):
    """Schema for creating a new image character."""

    user_id: UUID
    workspace_id: Optional[UUID] = None
