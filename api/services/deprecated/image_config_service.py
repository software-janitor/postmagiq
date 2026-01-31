"""Service for managing image prompt configuration."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import desc
from sqlmodel import select

from runner.content.ids import coerce_uuid, normalize_user_id
from runner.db.engine import get_session
from runner.db.models import (
    ImageScene,
    ImagePose,
    ImageOutfit,
    ImageProp,
    ImageCharacter,
    ImageConfigSet,
)
from runner.db.models import (
    SceneCharacter,
    PropCategory,
    ScenePropRule,
    ContextPropRule,
)


# Import default configurations from canonical source
from data.image_defaults import (
    DEFAULT_SCENES,
    DEFAULT_POSES,
    DEFAULT_OUTFITS,
    DEFAULT_PROPS,
    DEFAULT_ENGINEER,
    DEFAULT_ROBOT,
)


class ImageConfigService:
    """Service for managing image prompt configuration."""

    def __init__(self):
        pass

    def _resolve_user_id(self, user_id: Union[str, UUID]) -> UUID:
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        return uid

    def _resolve_id(self, value: Union[str, UUID]) -> UUID:
        vid = coerce_uuid(value)
        if not vid:
            raise ValueError("Invalid id")
        return vid

    def _serialize(self, record) -> dict:
        """Serialize SQLModel records into JSON-friendly dicts."""
        data = record.model_dump()
        for key, value in data.items():
            if isinstance(value, UUID):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    def _encode_prop_category(
        self, description: Optional[str], context: str, is_system: bool
    ) -> str:
        """Encode prop category metadata into description field."""
        return json.dumps(
            {
                "legacy": {
                    "description": description,
                    "context": context,
                    "is_system": is_system,
                }
            }
        )

    def _decode_prop_category(self, description: Optional[str]) -> dict:
        """Decode prop category metadata from description field."""
        if not description:
            return {"description": None, "context": "all", "is_system": False}
        try:
            payload = json.loads(description)
        except json.JSONDecodeError:
            return {"description": description, "context": "all", "is_system": False}
        legacy = payload.get("legacy") if isinstance(payload, dict) else None
        if isinstance(legacy, dict):
            return {
                "description": legacy.get("description"),
                "context": legacy.get("context", "all"),
                "is_system": legacy.get("is_system", False),
            }
        return {"description": description, "context": "all", "is_system": False}

    def seed_defaults(self, user_id: Union[str, UUID]) -> dict:
        """Seed default configurations for a user."""
        uid = self._resolve_user_id(user_id)
        counts = {"scenes": 0, "poses": 0, "outfits": 0, "props": 0, "characters": 0}

        with get_session() as session:
            existing = session.exec(
                select(ImageScene.id).where(ImageScene.user_id == uid).limit(1)
            ).first()
            if existing:
                return {"status": "already_seeded", "counts": counts}

            scenes = []
            for sentiment, scene_list in DEFAULT_SCENES.items():
                for scene in scene_list:
                    scenes.append(
                        ImageScene(
                            user_id=uid,
                            code=scene["code"],
                            name=scene["name"],
                            sentiment=sentiment,
                            viewpoint=scene.get("viewpoint", "standard"),
                            description=scene["desc"],
                            is_hardware_only=scene.get("is_hardware_only", False),
                            no_desk_props=scene.get("no_desk_props", False),
                        )
                    )
                    counts["scenes"] += 1

            poses = []
            for sentiment, pose_list in DEFAULT_POSES.items():
                for pose in pose_list:
                    poses.append(
                        ImagePose(
                            user_id=uid,
                            code=pose["code"],
                            sentiment=sentiment,
                            description=pose["desc"],
                            emotional_note=pose.get("note"),
                        )
                    )
                    counts["poses"] += 1

            outfits = [
                ImageOutfit(
                    user_id=uid,
                    vest=outfit["vest"],
                    shirt=outfit["shirt"],
                    pants=outfit.get("pants", "Dark pants"),
                )
                for outfit in DEFAULT_OUTFITS
            ]
            counts["outfits"] = len(outfits)

            props = []
            for category, prop_list in DEFAULT_PROPS.items():
                for prop in prop_list:
                    props.append(
                        ImageProp(
                            user_id=uid,
                            category=category,
                            description=prop["desc"],
                            context=prop.get("context", "all"),
                        )
                    )
                    counts["props"] += 1

            characters = [
                ImageCharacter(
                    user_id=uid,
                    character_type="engineer",
                    appearance=DEFAULT_ENGINEER["appearance"],
                    face_details=DEFAULT_ENGINEER["face_details"],
                    clothing_rules=DEFAULT_ENGINEER["clothing_rules"],
                ),
                ImageCharacter(
                    user_id=uid,
                    character_type="robot",
                    appearance=DEFAULT_ROBOT["appearance"],
                    face_details=DEFAULT_ROBOT["face_details"],
                    clothing_rules=DEFAULT_ROBOT["clothing_rules"],
                ),
            ]
            counts["characters"] = len(characters)

            session.add_all(scenes + poses + outfits + props + characters)
            session.commit()

        return {"status": "seeded", "counts": counts}

    def reset_defaults(self, user_id: Union[str, UUID]) -> dict:
        """Delete all config for a user and re-seed with defaults."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            for model in (
                ImageScene,
                ImagePose,
                ImageOutfit,
                ImageProp,
                ImageCharacter,
            ):
                rows = session.exec(select(model).where(model.user_id == uid)).all()
                for row in rows:
                    session.delete(row)
            session.commit()

        return self.seed_defaults(user_id)

    # =========================================================================
    # Scene CRUD
    # =========================================================================

    def get_scenes(
        self, user_id: Union[str, UUID], sentiment: Optional[str] = None
    ) -> list[dict]:
        """Get all scenes for a user, optionally filtered by sentiment."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(ImageScene).where(ImageScene.user_id == uid)
            if sentiment:
                statement = statement.where(ImageScene.sentiment == sentiment).order_by(
                    ImageScene.code
                )
            else:
                statement = statement.order_by(ImageScene.sentiment, ImageScene.code)
            return [self._serialize(s) for s in session.exec(statement).all()]

    def get_scene(self, scene_id: Union[str, UUID]) -> Optional[dict]:
        """Get a single scene."""
        sid = self._resolve_id(scene_id)
        with get_session() as session:
            record = session.get(ImageScene, sid)
            return self._serialize(record) if record else None

    def update_scene(self, scene_id: Union[str, UUID], **kwargs) -> None:
        """Update a scene."""
        sid = self._resolve_id(scene_id)
        with get_session() as session:
            record = session.get(ImageScene, sid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    def create_scene(
        self,
        user_id: Union[str, UUID],
        code: str,
        name: str,
        sentiment: str,
        description: str,
        viewpoint: str = "standard",
        is_hardware_only: bool = False,
        no_desk_props: bool = False,
    ) -> str:
        """Create a new scene."""
        uid = self._resolve_user_id(user_id)
        record = ImageScene(
            user_id=uid,
            code=code,
            name=name,
            sentiment=sentiment,
            viewpoint=viewpoint,
            description=description,
            is_hardware_only=is_hardware_only,
            no_desk_props=no_desk_props,
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def delete_scene(self, scene_id: Union[str, UUID]) -> None:
        """Delete a scene."""
        sid = self._resolve_id(scene_id)
        with get_session() as session:
            record = session.get(ImageScene, sid)
            if not record:
                return
            session.delete(record)
            session.commit()

    # =========================================================================
    # Pose CRUD
    # =========================================================================

    def get_poses(
        self, user_id: Union[str, UUID], sentiment: Optional[str] = None
    ) -> list[dict]:
        """Get all poses for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(ImagePose).where(ImagePose.user_id == uid)
            if sentiment:
                statement = statement.where(ImagePose.sentiment == sentiment).order_by(
                    ImagePose.code
                )
            else:
                statement = statement.order_by(ImagePose.sentiment, ImagePose.code)
            return [self._serialize(p) for p in session.exec(statement).all()]

    def update_pose(self, pose_id: Union[str, UUID], **kwargs) -> None:
        """Update a pose."""
        pid = self._resolve_id(pose_id)
        with get_session() as session:
            record = session.get(ImagePose, pid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    def create_pose(
        self,
        user_id: Union[str, UUID],
        code: str,
        sentiment: str,
        description: str,
        emotional_note: str = None,
    ) -> str:
        """Create a new pose."""
        uid = self._resolve_user_id(user_id)
        record = ImagePose(
            user_id=uid,
            code=code,
            sentiment=sentiment,
            description=description,
            emotional_note=emotional_note,
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def delete_pose(self, pose_id: Union[str, UUID]) -> None:
        """Delete a pose."""
        pid = self._resolve_id(pose_id)
        with get_session() as session:
            record = session.get(ImagePose, pid)
            if not record:
                return
            session.delete(record)
            session.commit()

    # =========================================================================
    # Outfit CRUD
    # =========================================================================

    def get_outfits(self, user_id: Union[str, UUID]) -> list[dict]:
        """Get all outfits for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = (
                select(ImageOutfit)
                .where(ImageOutfit.user_id == uid)
                .order_by(ImageOutfit.created_at)
            )
            return [self._serialize(o) for o in session.exec(statement).all()]

    def update_outfit(self, outfit_id: Union[str, UUID], **kwargs) -> None:
        """Update an outfit."""
        oid = self._resolve_id(outfit_id)
        with get_session() as session:
            record = session.get(ImageOutfit, oid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    def create_outfit(
        self,
        user_id: Union[str, UUID],
        vest: str,
        shirt: str,
        pants: str = "Dark pants",
    ) -> str:
        """Create a new outfit."""
        uid = self._resolve_user_id(user_id)
        record = ImageOutfit(user_id=uid, vest=vest, shirt=shirt, pants=pants)
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def delete_outfit(self, outfit_id: Union[str, UUID]) -> None:
        """Delete an outfit."""
        oid = self._resolve_id(outfit_id)
        with get_session() as session:
            record = session.get(ImageOutfit, oid)
            if not record:
                return
            session.delete(record)
            session.commit()

    def bulk_import_outfits(
        self, user_id: Union[str, UUID], outfits: list[dict]
    ) -> dict:
        """Bulk import outfits from a list of dicts.

        Each dict should have: vest, shirt, pants (optional, defaults to 'Dark pants')

        Returns: {"imported": count, "skipped": count, "errors": []}
        """
        imported = 0
        skipped = 0
        errors = []

        uid = self._resolve_user_id(user_id)
        existing = set()
        with get_session() as session:
            existing_rows = session.exec(
                select(ImageOutfit).where(ImageOutfit.user_id == uid)
            ).all()
            for row in existing_rows:
                existing.add((row.vest.lower(), row.shirt.lower(), row.pants.lower()))

            for i, outfit in enumerate(outfits):
                try:
                    vest = outfit.get("vest", "").strip()
                    shirt = outfit.get("shirt", "").strip()
                    pants = outfit.get("pants", "Dark pants").strip()

                    if not vest or not shirt:
                        errors.append(f"Row {i + 1}: Missing vest or shirt")
                        continue

                    # Check for duplicate
                    key = (vest.lower(), shirt.lower(), pants.lower())
                    if key in existing:
                        skipped += 1
                        continue

                    # Insert
                    session.add(
                        ImageOutfit(user_id=uid, vest=vest, shirt=shirt, pants=pants)
                    )
                    existing.add(key)
                    imported += 1

                except Exception as e:
                    errors.append(f"Row {i + 1}: {str(e)}")

            session.commit()
        return {"imported": imported, "skipped": skipped, "errors": errors}

    # =========================================================================
    # Props CRUD
    # =========================================================================

    def get_props(
        self, user_id: Union[str, UUID], category: Optional[str] = None
    ) -> list[dict]:
        """Get all props for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(ImageProp).where(ImageProp.user_id == uid)
            if category:
                statement = statement.where(ImageProp.category == category)
            else:
                statement = statement.order_by(ImageProp.category)
            return [self._serialize(p) for p in session.exec(statement).all()]

    def update_prop(self, prop_id: Union[str, UUID], **kwargs) -> None:
        """Update a prop."""
        pid = self._resolve_id(prop_id)
        with get_session() as session:
            record = session.get(ImageProp, pid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    def create_prop(
        self,
        user_id: Union[str, UUID],
        category: str,
        description: str,
        context: str = "all",
    ) -> str:
        """Create a new prop."""
        uid = self._resolve_user_id(user_id)
        record = ImageProp(
            user_id=uid, category=category, description=description, context=context
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def delete_prop(self, prop_id: Union[str, UUID]) -> None:
        """Delete a prop."""
        pid = self._resolve_id(prop_id)
        with get_session() as session:
            record = session.get(ImageProp, pid)
            if not record:
                return
            session.delete(record)
            session.commit()

    # =========================================================================
    # Character CRUD
    # =========================================================================

    def get_characters(self, user_id: Union[str, UUID]) -> list[dict]:
        """Get all character definitions for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = (
                select(ImageCharacter)
                .where(ImageCharacter.user_id == uid)
                .order_by(ImageCharacter.character_type)
            )
            return [self._serialize(c) for c in session.exec(statement).all()]

    def get_character(
        self, user_id: Union[str, UUID], character_type: str
    ) -> Optional[dict]:
        """Get a specific character definition."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(ImageCharacter).where(
                ImageCharacter.user_id == uid,
                ImageCharacter.character_type == character_type,
            )
            record = session.exec(statement).first()
            return self._serialize(record) if record else None

    def update_character(self, character_id: Union[str, UUID], **kwargs) -> None:
        """Update a character."""
        cid = self._resolve_id(character_id)
        with get_session() as session:
            record = session.get(ImageCharacter, cid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    # =========================================================================
    # Config Set CRUD
    # =========================================================================

    def get_config_sets(self, user_id: Union[str, UUID]) -> list[dict]:
        """Get all config sets for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = (
                select(ImageConfigSet)
                .where(ImageConfigSet.user_id == uid)
                .order_by(desc(ImageConfigSet.is_default), ImageConfigSet.created_at)
            )
            return [self._serialize(cs) for cs in session.exec(statement).all()]

    def get_config_set(self, config_set_id: Union[str, UUID]) -> Optional[dict]:
        """Get a single config set."""
        cid = self._resolve_id(config_set_id)
        with get_session() as session:
            record = session.get(ImageConfigSet, cid)
            return self._serialize(record) if record else None

    def create_config_set(
        self,
        user_id: Union[str, UUID],
        name: str,
        description: Optional[str] = None,
        is_default: bool = False,
    ) -> str:
        """Create a new config set."""
        uid = self._resolve_user_id(user_id)
        record = ImageConfigSet(
            user_id=uid,
            name=name,
            description=description,
            is_default=is_default,
        )
        with get_session() as session:
            if is_default:
                existing = session.exec(
                    select(ImageConfigSet).where(ImageConfigSet.user_id == uid)
                ).all()
                for item in existing:
                    item.is_default = False
                    session.add(item)
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def update_config_set(self, config_set_id: Union[str, UUID], **kwargs) -> None:
        """Update a config set."""
        cid = self._resolve_id(config_set_id)
        with get_session() as session:
            record = session.get(ImageConfigSet, cid)
            if not record:
                return
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    def set_default_config_set(
        self, user_id: Union[str, UUID], config_set_id: Union[str, UUID]
    ) -> None:
        """Set a config set as the default."""
        uid = self._resolve_user_id(user_id)
        cid = self._resolve_id(config_set_id)
        with get_session() as session:
            records = session.exec(
                select(ImageConfigSet).where(ImageConfigSet.user_id == uid)
            ).all()
            for record in records:
                record.is_default = record.id == cid
                session.add(record)
            session.commit()

    def clone_config_set(self, config_set_id: Union[str, UUID], new_name: str) -> str:
        """Clone a config set with a new name."""
        cid = self._resolve_id(config_set_id)
        with get_session() as session:
            record = session.get(ImageConfigSet, cid)
            if not record:
                raise ValueError("Config set not found")
            clone = ImageConfigSet(
                user_id=record.user_id,
                name=new_name,
                description=record.description,
                is_default=False,
            )
            session.add(clone)
            session.commit()
            session.refresh(clone)
            return str(clone.id)

    def delete_config_set(self, config_set_id: Union[str, UUID]) -> None:
        """Delete a config set."""
        cid = self._resolve_id(config_set_id)
        with get_session() as session:
            record = session.get(ImageConfigSet, cid)
            if not record:
                return
            session.delete(record)
            session.commit()

    # =========================================================================
    # Scene-Character Integration
    # =========================================================================

    def get_scene_characters(self, scene_id: Union[str, UUID]) -> list[dict]:
        """Get all characters linked to a scene."""
        sid = self._resolve_id(scene_id)
        with get_session() as session:
            statement = (
                select(SceneCharacter)
                .where(SceneCharacter.scene_id == sid)
                .order_by(SceneCharacter.position)
            )
            records = session.exec(statement).all()
            return [
                {
                    "id": str(r.id),
                    "scene_id": str(r.scene_id),
                    "character_id": str(r.character_id),
                    "outfit_id": None,
                    "position": r.position,
                }
                for r in records
            ]

    def add_scene_character(
        self,
        scene_id: Union[str, UUID],
        character_id: Union[str, UUID],
        outfit_id: Optional[Union[str, UUID]] = None,
        position: Optional[str] = None,
    ) -> str:
        """Add a character to a scene."""
        sid = self._resolve_id(scene_id)
        cid = self._resolve_id(character_id)
        with get_session() as session:
            existing = session.exec(
                select(SceneCharacter).where(
                    SceneCharacter.scene_id == sid,
                    SceneCharacter.character_id == cid,
                )
            ).first()
            if existing:
                existing.position = position
                session.add(existing)
                session.commit()
                return str(existing.id)
            record = SceneCharacter(scene_id=sid, character_id=cid, position=position)
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def remove_scene_character(
        self, scene_id: Union[str, UUID], character_id: Union[str, UUID]
    ) -> None:
        """Remove a character from a scene."""
        sid = self._resolve_id(scene_id)
        cid = self._resolve_id(character_id)
        with get_session() as session:
            record = session.exec(
                select(SceneCharacter).where(
                    SceneCharacter.scene_id == sid,
                    SceneCharacter.character_id == cid,
                )
            ).first()
            if not record:
                return
            session.delete(record)
            session.commit()

    def update_scene_character(
        self,
        scene_id: Union[str, UUID],
        character_id: Union[str, UUID],
        outfit_id: Optional[Union[str, UUID]] = None,
        position: Optional[str] = None,
    ) -> None:
        """Update a character's outfit or position in a scene."""
        sid = self._resolve_id(scene_id)
        cid = self._resolve_id(character_id)
        with get_session() as session:
            record = session.exec(
                select(SceneCharacter).where(
                    SceneCharacter.scene_id == sid,
                    SceneCharacter.character_id == cid,
                )
            ).first()
            if not record:
                return
            record.position = position
            session.add(record)
            session.commit()

    # =========================================================================
    # Prop Categories
    # =========================================================================

    def get_prop_categories(self, user_id: Union[str, UUID]) -> list[dict]:
        """Get all prop categories for a user."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            records = session.exec(
                select(PropCategory)
                .where(PropCategory.user_id == uid)
                .order_by(PropCategory.name)
            ).all()
            results = []
            for record in records:
                meta = self._decode_prop_category(record.description)
                results.append(
                    {
                        "id": str(record.id),
                        "user_id": str(record.user_id),
                        "name": record.name,
                        "description": meta["description"],
                        "context": meta["context"],
                        "is_system": meta["is_system"],
                    }
                )
            return results

    def get_prop_category(self, category_id: Union[str, UUID]) -> Optional[dict]:
        """Get a single prop category."""
        cid = self._resolve_id(category_id)
        with get_session() as session:
            record = session.get(PropCategory, cid)
            if not record:
                return None
            meta = self._decode_prop_category(record.description)
            return {
                "id": str(record.id),
                "user_id": str(record.user_id),
                "name": record.name,
                "description": meta["description"],
                "context": meta["context"],
                "is_system": meta["is_system"],
            }

    def create_prop_category(
        self,
        user_id: Union[str, UUID],
        name: str,
        description: Optional[str] = None,
        context: str = "all",
    ) -> str:
        """Create a new prop category."""
        uid = self._resolve_user_id(user_id)
        record = PropCategory(
            user_id=uid,
            name=name,
            description=self._encode_prop_category(description, context, False),
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def update_prop_category(self, category_id: Union[str, UUID], **kwargs) -> None:
        """Update a prop category."""
        cid = self._resolve_id(category_id)
        with get_session() as session:
            record = session.get(PropCategory, cid)
            if not record:
                return
            if any(key in kwargs for key in ("description", "context", "is_system")):
                meta = self._decode_prop_category(record.description)
                description = kwargs.pop("description", meta["description"])
                context = kwargs.pop("context", meta["context"])
                is_system = kwargs.pop("is_system", meta["is_system"])
                record.description = self._encode_prop_category(
                    description, context, is_system
                )
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()

    def delete_prop_category(self, category_id: Union[str, UUID]) -> None:
        """Delete a prop category."""
        cid = self._resolve_id(category_id)
        with get_session() as session:
            record = session.get(PropCategory, cid)
            if not record:
                return
            session.delete(record)
            session.commit()

    # =========================================================================
    # Scene Prop Rules
    # =========================================================================

    def get_scene_prop_rules(self, scene_id: Union[str, UUID]) -> list[dict]:
        """Get all prop rules for a scene."""
        sid = self._resolve_id(scene_id)
        with get_session() as session:
            records = session.exec(
                select(ScenePropRule).where(ScenePropRule.scene_id == sid)
            ).all()
            return [
                {
                    "id": str(r.id),
                    "scene_id": str(r.scene_id),
                    "prop_category_id": str(r.prop_category_id),
                    "prop_id": None,
                    "required": r.is_required,
                    "excluded": False,
                    "max_count": r.max_count or 1,
                }
                for r in records
            ]

    def add_scene_prop_rule(
        self,
        scene_id: Union[str, UUID],
        prop_category_id: Optional[Union[str, UUID]] = None,
        prop_id: Optional[Union[str, UUID]] = None,
        required: bool = False,
        excluded: bool = False,
        max_count: int = 1,
    ) -> str:
        """Add a prop rule to a scene."""
        if prop_id is not None:
            raise ValueError("prop_id rules are not supported in Postgres schema")
        sid = self._resolve_id(scene_id)
        if not prop_category_id:
            raise ValueError("prop_category_id is required")
        pcid = self._resolve_id(prop_category_id)
        record = ScenePropRule(
            scene_id=sid,
            prop_category_id=pcid,
            is_required=required,
            max_count=max_count,
        )
        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def remove_scene_prop_rule(self, rule_id: Union[str, UUID]) -> None:
        """Remove a scene prop rule."""
        rid = self._resolve_id(rule_id)
        with get_session() as session:
            record = session.get(ScenePropRule, rid)
            if not record:
                return
            session.delete(record)
            session.commit()

    # =========================================================================
    # Context Prop Rules
    # =========================================================================

    def get_context_prop_rules(
        self, user_id: Union[str, UUID], context: Optional[str] = None
    ) -> list[dict]:
        """Get context-based prop rules."""
        uid = self._resolve_user_id(user_id)
        with get_session() as session:
            statement = select(ContextPropRule, PropCategory).where(
                ContextPropRule.prop_category_id == PropCategory.id,
                PropCategory.user_id == uid,
            )
            if context:
                statement = statement.where(ContextPropRule.context == context)
            records = session.exec(statement).all()
            results = []
            for rule, category in records:
                results.append(
                    {
                        "id": str(rule.id),
                        "user_id": str(category.user_id),
                        "context": rule.context,
                        "prop_category_id": str(rule.prop_category_id),
                        "weight": 1 if rule.is_required else 0,
                    }
                )
            return results

    def set_context_prop_rule(
        self,
        user_id: Union[str, UUID],
        context: str,
        prop_category_id: Union[str, UUID],
        weight: int = 1,
    ) -> str:
        """Set a context-based prop rule."""
        self._resolve_user_id(user_id)
        pcid = self._resolve_id(prop_category_id)
        is_required = weight > 0
        with get_session() as session:
            existing = session.exec(
                select(ContextPropRule).where(
                    ContextPropRule.context == context,
                    ContextPropRule.prop_category_id == pcid,
                )
            ).first()
            if existing:
                existing.is_required = is_required
                session.add(existing)
                session.commit()
                return str(existing.id)
            record = ContextPropRule(
                context=context,
                prop_category_id=pcid,
                is_required=is_required,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return str(record.id)

    def remove_context_prop_rule(self, rule_id: Union[str, UUID]) -> None:
        """Remove a context prop rule."""
        rid = self._resolve_id(rule_id)
        with get_session() as session:
            record = session.get(ContextPropRule, rid)
            if not record:
                return
            session.delete(record)
            session.commit()
