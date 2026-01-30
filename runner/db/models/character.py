"""Character models: CharacterTemplate, OutfitPart, Outfit, Character, etc."""

from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# CharacterTemplate
# =============================================================================


class CharacterTemplateBase(SQLModel):
    """Base character template fields."""

    name: str
    description: Optional[str] = None
    base_appearance: str
    is_active: bool = Field(default=True)


class CharacterTemplate(UUIDModel, CharacterTemplateBase, TimestampMixin, table=True):
    """CharacterTemplate table - reusable character definitions."""

    __tablename__ = "character_templates"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class CharacterTemplateCreate(CharacterTemplateBase):
    """Schema for creating a new character template."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# OutfitPart
# =============================================================================


class OutfitPartBase(SQLModel):
    """Base outfit part fields."""

    category: str  # vest, shirt, pants, accessories
    name: str
    description: str
    color: Optional[str] = None
    is_active: bool = Field(default=True)


class OutfitPart(UUIDModel, OutfitPartBase, TimestampMixin, table=True):
    """OutfitPart table - individual clothing items."""

    __tablename__ = "outfit_parts"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class OutfitPartCreate(OutfitPartBase):
    """Schema for creating a new outfit part."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# Outfit
# =============================================================================


class OutfitBase(SQLModel):
    """Base outfit fields."""

    name: str
    description: Optional[str] = None
    is_default: bool = Field(default=False)


class Outfit(UUIDModel, OutfitBase, TimestampMixin, table=True):
    """Outfit table - named outfit combinations."""

    __tablename__ = "outfits"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class OutfitCreate(OutfitBase):
    """Schema for creating a new outfit."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# OutfitItem
# =============================================================================


class OutfitItemBase(SQLModel):
    """Base outfit item fields (junction table)."""

    pass


class OutfitItem(UUIDModel, OutfitItemBase, table=True):
    """OutfitItem table - links outfits to outfit parts."""

    __tablename__ = "outfit_items"

    outfit_id: UUID = Field(foreign_key="outfits.id", index=True)
    outfit_part_id: UUID = Field(foreign_key="outfit_parts.id", index=True)


class OutfitItemCreate(OutfitItemBase):
    """Schema for creating a new outfit item."""

    outfit_id: UUID
    outfit_part_id: UUID


# =============================================================================
# Character
# =============================================================================


class CharacterBase(SQLModel):
    """Base character fields."""

    name: str
    description: Optional[str] = None
    is_active: bool = Field(default=True)


class Character(UUIDModel, CharacterBase, TimestampMixin, table=True):
    """Character table - instantiated characters from templates."""

    __tablename__ = "characters"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    template_id: Optional[UUID] = Field(
        default=None, foreign_key="character_templates.id"
    )
    default_outfit_id: Optional[UUID] = Field(default=None, foreign_key="outfits.id")

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class CharacterCreate(CharacterBase):
    """Schema for creating a new character."""

    user_id: UUID
    template_id: Optional[UUID] = None
    default_outfit_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


# =============================================================================
# CharacterOutfit
# =============================================================================


class CharacterOutfitBase(SQLModel):
    """Base character outfit fields (junction table)."""

    pass


class CharacterOutfit(UUIDModel, CharacterOutfitBase, table=True):
    """CharacterOutfit table - links characters to available outfits."""

    __tablename__ = "character_outfits"

    character_id: UUID = Field(foreign_key="characters.id", index=True)
    outfit_id: UUID = Field(foreign_key="outfits.id", index=True)


class CharacterOutfitCreate(CharacterOutfitBase):
    """Schema for creating a new character outfit."""

    character_id: UUID
    outfit_id: UUID


# =============================================================================
# Sentiment
# =============================================================================


class SentimentBase(SQLModel):
    """Base sentiment fields."""

    name: str
    description: Optional[str] = None
    color_code: Optional[str] = None  # For UI display


class Sentiment(UUIDModel, SentimentBase, TimestampMixin, table=True):
    """Sentiment table - emotional states for scenes."""

    __tablename__ = "sentiments"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class SentimentCreate(SentimentBase):
    """Schema for creating a new sentiment."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# SceneCharacter
# =============================================================================


class SceneCharacterBase(SQLModel):
    """Base scene character fields (junction table)."""

    position: Optional[str] = None  # e.g., "left", "center", "right"


class SceneCharacter(UUIDModel, SceneCharacterBase, table=True):
    """SceneCharacter table - links scenes to characters."""

    __tablename__ = "scene_characters"

    scene_id: UUID = Field(foreign_key="image_scenes.id", index=True)
    character_id: UUID = Field(foreign_key="characters.id", index=True)


class SceneCharacterCreate(SceneCharacterBase):
    """Schema for creating a new scene character."""

    scene_id: UUID
    character_id: UUID


# =============================================================================
# PropCategory
# =============================================================================


class PropCategoryBase(SQLModel):
    """Base prop category fields."""

    name: str
    description: Optional[str] = None


class PropCategory(UUIDModel, PropCategoryBase, TimestampMixin, table=True):
    """PropCategory table - categories for desk props."""

    __tablename__ = "prop_categories"

    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Multi-tenancy: workspace_id is nullable for migration compatibility
    workspace_id: Optional[UUID] = Field(
        default=None,
        foreign_key="workspaces.id",
        index=True,
    )


class PropCategoryCreate(PropCategoryBase):
    """Schema for creating a new prop category."""

    user_id: UUID
    workspace_id: Optional[UUID] = None


# =============================================================================
# ScenePropRule
# =============================================================================


class ScenePropRuleBase(SQLModel):
    """Base scene prop rule fields."""

    is_required: bool = Field(default=False)
    max_count: Optional[int] = None


class ScenePropRule(UUIDModel, ScenePropRuleBase, table=True):
    """ScenePropRule table - rules for props in scenes."""

    __tablename__ = "scene_prop_rules"

    scene_id: UUID = Field(foreign_key="image_scenes.id", index=True)
    prop_category_id: UUID = Field(foreign_key="prop_categories.id", index=True)


class ScenePropRuleCreate(ScenePropRuleBase):
    """Schema for creating a new scene prop rule."""

    scene_id: UUID
    prop_category_id: UUID


# =============================================================================
# ContextPropRule
# =============================================================================


class ContextPropRuleBase(SQLModel):
    """Base context prop rule fields."""

    context: str  # "software", "hardware", "all"
    is_required: bool = Field(default=False)


class ContextPropRule(UUIDModel, ContextPropRuleBase, table=True):
    """ContextPropRule table - rules for props based on context."""

    __tablename__ = "context_prop_rules"

    prop_category_id: UUID = Field(foreign_key="prop_categories.id", index=True)


class ContextPropRuleCreate(ContextPropRuleBase):
    """Schema for creating a new context prop rule."""

    prop_category_id: UUID
