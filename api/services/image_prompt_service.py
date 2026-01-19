"""Service for generating image prompts for posts."""

import random
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import desc, func
from sqlmodel import select

from runner.content.ids import coerce_uuid, normalize_user_id
from runner.content.models import ImagePromptResponse
from runner.db.engine import get_session
from runner.db.models import ImagePrompt
from api.services.image_config_service import ImageConfigService

# Import defaults from canonical source for fallback
from data.image_defaults import (
    DEFAULT_SCENES,
    DEFAULT_POSES,
    DEFAULT_OUTFITS,
    DEFAULT_PROPS,
)

ROBOT_COLORS = {
    "SUCCESS": "CYAN/BLUE",
    "FAILURE": "RED",
    "UNRESOLVED": "AMBER/YELLOW",
}

ROBOT_EXPRESSIONS = {
    "SUCCESS": "happy face (simple upturned curved line for smile, two dots for eyes angled up)",
    "FAILURE": "distressed face (downturned curved line, two dots for eyes angled down, pixel sweat drop)",
    "UNRESOLVED": "thinking face (three animated dots, or single question mark symbol)",
}

ENGINEER_EXPRESSIONS = {
    "SUCCESS": "satisfied expression, slight smile, relaxed",
    "FAILURE": "frustrated expression, furrowed brow, tense jaw, no smile",
    "UNRESOLVED": "thoughtful expression, slight furrow, contemplative",
}

class ImagePromptService:
    """Service for generating and managing image prompts."""

    def __init__(self):
        self.config_service = ImageConfigService()

    def _record_to_response(self, record: ImagePrompt) -> ImagePromptResponse:
        """Convert a database record to API response."""
        return ImagePromptResponse(
            id=str(record.id),
            post_id=record.post_id,
            sentiment=record.sentiment,
            context=record.context,
            scene_code=record.scene_code,
            scene_name=record.scene_name,
            pose_code=record.pose_code,
            outfit_vest=record.outfit_vest,
            outfit_shirt=record.outfit_shirt,
            prompt_content=record.prompt_content,
            version=record.version,
            image_data=record.image_data,
            has_image=record.image_data is not None,
            created_at=record.created_at.isoformat() if record.created_at else None,
        )

    def update_image(self, prompt_id: Union[str, UUID], image_data: str) -> None:
        """Update the image_data for a prompt."""
        pid = coerce_uuid(prompt_id)
        if not pid:
            raise ValueError("Invalid prompt_id")
        with get_session() as session:
            record = session.get(ImagePrompt, pid)
            if not record:
                return
            record.image_data = image_data
            session.add(record)
            session.commit()

    def _get_random_desk_props(self, user_id: Union[str, UUID], context: str = "software") -> list[str]:
        """Select random desk props from database."""
        props = set()

        # Get props by category from database
        all_props = self.config_service.get_props(user_id)

        # Group by category
        by_category = {}
        for p in all_props:
            cat = p.get("category", "other")
            ctx = p.get("context", "all")
            # Filter by context (all, software, hardware)
            if ctx == "all" or ctx == context:
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(p["description"])

        # Pick one from each category (if available)
        for category in ["notes", "drinks", "other"]:
            if category in by_category and by_category[category]:
                props.add(random.choice(by_category[category]))

        # Add hardware props if hardware context
        if context == "hardware" and "hardware" in by_category and by_category["hardware"]:
            props.add(random.choice(by_category["hardware"]))

        # Fallback to defaults from data/image_defaults.py if database is empty
        if not props:
            # Pick one from each category
            for category in ["notes", "drinks", "tech"]:
                if category in DEFAULT_PROPS:
                    cat_props = [p["desc"] for p in DEFAULT_PROPS[category] if p.get("context", "all") in ("all", context)]
                    if cat_props:
                        props.add(random.choice(cat_props))
            # Add hardware props if hardware context
            if context == "hardware":
                for hw_cat in ["hardware_boards", "hardware_tools"]:
                    if hw_cat in DEFAULT_PROPS:
                        hw_props = [p["desc"] for p in DEFAULT_PROPS[hw_cat]]
                        if hw_props:
                            props.add(random.choice(hw_props))
                            break  # Only add one hardware prop

        return list(props)

    def _generate_prompt_content(
        self,
        title: str,
        sentiment: str,
        user_id: Union[str, UUID],
        context: str = "software",
        scene: Optional[dict] = None,
        pose_code: Optional[str] = None,
        outfit: Optional[dict] = None,
        is_field_note: bool = False,
    ) -> tuple[str, dict]:
        """Generate the image prompt content and return metadata.

        Args:
            user_id: User ID (required for multi-tenancy)
        """
        # Pick scene from database, fallback to defaults
        db_scenes = self.config_service.get_scenes(user_id, sentiment)
        if db_scenes:
            scenes = [{"code": s["code"], "name": s["name"], "desc": s["description"]} for s in db_scenes]
        else:
            # Fallback to defaults from data/image_defaults.py
            default_scenes = DEFAULT_SCENES.get(sentiment, DEFAULT_SCENES["SUCCESS"])
            scenes = [{"code": s["code"], "name": s["name"], "desc": s["desc"]} for s in default_scenes]

        if not scene:
            scene = random.choice(scenes)

        # Pick outfit from database, fallback to defaults
        if not outfit:
            db_outfits = self.config_service.get_outfits(user_id)
            if db_outfits:
                db_outfit = random.choice(db_outfits)
                outfit = {"vest": db_outfit["vest"], "shirt": db_outfit["shirt"]}
            else:
                # Fallback to defaults from data/image_defaults.py
                default_outfit = random.choice(DEFAULT_OUTFITS)
                outfit = {"vest": default_outfit["vest"], "shirt": default_outfit["shirt"]}

        # Pick pose from database, fallback to defaults
        db_poses = self.config_service.get_poses(user_id, sentiment)
        pose_desc = "neutral standing pose"
        # Build fallback pose lookup from defaults
        default_poses_for_sentiment = DEFAULT_POSES.get(sentiment, DEFAULT_POSES["SUCCESS"])
        default_pose_lookup = {p["code"]: p["desc"] for p in default_poses_for_sentiment}

        if not pose_code:
            if db_poses:
                db_pose = random.choice(db_poses)
                pose_code = db_pose["code"]
                pose_desc = db_pose["description"]
            else:
                # Fallback to defaults from data/image_defaults.py
                default_pose = random.choice(default_poses_for_sentiment)
                pose_code = default_pose["code"]
                pose_desc = default_pose["desc"]
        else:
            # Look up pose description from database first, then defaults
            matching = [p for p in db_poses if p["code"] == pose_code]
            if matching:
                pose_desc = matching[0]["description"]
            else:
                pose_desc = default_pose_lookup.get(pose_code, "neutral standing pose")
        robot_color = ROBOT_COLORS.get(sentiment, "CYAN/BLUE")
        robot_expression = ROBOT_EXPRESSIONS.get(sentiment, "neutral expression")
        engineer_expression = ENGINEER_EXPRESSIONS.get(sentiment, "neutral expression")

        # Desk props from database
        props = self._get_random_desk_props(user_id, context)
        props_list = "\n".join(f"- {p}" for p in props)
        desk_props_section = f"\n**Desk Props (naturally scattered):**\n{props_list}\n"

        # Layout section
        if is_field_note:
            layout_section = """**Layout:**
- NO title bar. The image fills the entire canvas (full bleed on all edges).
- NO text anywhere in the image."""
            title_section = ""
        else:
            layout_section = """**Layout:**
- Slim black title bar at top with title in white text, centered.
- Illustration fills the rest of the canvas (full bleed on left, right, bottom edges).
- The ONLY text in the image is the title."""
            title_section = f"\n**Title:** {title}\n"

        prompt = f"""## Image Prompt
{title_section}
**Style:** Modern graphic novel / editorial illustration. Clean, semi-realistic proportions. Thick confident ink lines. Muted slate blues, dark grays, crisp whites. 16:9 landscape.

{layout_section}

**Scene:** {scene['name']}
{scene['desc']}
{desk_props_section}
**The Engineer (IMPORTANT - follow exactly):**
- POSE: {pose_desc} ({pose_code})
- CLOTHING: {outfit['vest']} (buttoned up) over {outfit['shirt']} shirt. Open collar (NO TIE). Sleeves rolled up to forearms. Dark pants.
- Male, mid-30s, youthful.

**FACE (CRITICAL - follow exactly):**
- SKIN: Medium-dark skin, warm olive undertones.
- FACE SHAPE: Broad face, strong jawline, squared chin, fuller cheeks.
- EYEBROWS: Thick dark eyebrows with subtle arch.
- EYES: Large almond-shaped dark brown eyes.
- NOSE: Wide nose with rounded tip.
- LIPS: Full, clearly visible lips with natural color.
- EXPRESSION: {engineer_expression}
- HAIR: Long straight black hair, center-parted, tied back in ponytail.
- FACIAL HAIR: CIRCLE BEARD ONLY (mustache + chin beard connected). CLEAN SHAVEN cheeks/jawline.
- Framed from waist up.

**The Robot Companion (MUST INCLUDE):**
- Small hovering robot near the Engineer. Roughly 12 inches diameter.
- Round/oval white metal body with {robot_color} glowing trim.
- FACE IS A FLAT SCREEN ONLY: Simple black rectangular display panel showing {robot_expression}.
- Small antenna on top. Floats/hovers, no legs.

Generate the image now.
"""

        metadata = {
            "scene_code": scene["code"],
            "scene_name": scene["name"],
            "pose_code": pose_code,
            "outfit_vest": outfit["vest"],
            "outfit_shirt": outfit["shirt"],
        }

        return prompt, metadata

    def generate_prompt(
        self,
        user_id: Union[str, UUID],
        post_id: str,
        title: str,
        sentiment: str,
        context: str = "software",
        scene_code: Optional[str] = None,
        pose_code: Optional[str] = None,
        is_field_note: bool = False,
    ) -> ImagePromptResponse:
        """Generate and save an image prompt."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")

        # Get next version
        with get_session() as session:
            statement = select(func.max(ImagePrompt.version)).where(
                ImagePrompt.user_id == uid,
                ImagePrompt.post_id == post_id,
            )
            max_version = session.exec(statement).one()
            version = (max_version or 0) + 1

        # Get scene from database if code provided
        scene = None
        if scene_code:
            db_scenes = self.config_service.get_scenes(user_id, sentiment)
            matching = [s for s in db_scenes if s["code"] == scene_code]
            if matching:
                s = matching[0]
                scene = {"code": s["code"], "name": s["name"], "desc": s["description"]}

        # Generate prompt
        prompt_content, metadata = self._generate_prompt_content(
            title=title,
            sentiment=sentiment,
            context=context,
            scene=scene,
            pose_code=pose_code,
            is_field_note=is_field_note,
            user_id=user_id,
        )

        # Save to database
        record = ImagePrompt(
            user_id=uid,
            post_id=post_id,
            sentiment=sentiment,
            context=context,
            scene_code=metadata["scene_code"],
            scene_name=metadata["scene_name"],
            pose_code=metadata["pose_code"],
            outfit_vest=metadata["outfit_vest"],
            outfit_shirt=metadata["outfit_shirt"],
            prompt_content=prompt_content,
            version=version,
        )

        with get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)

        return self._record_to_response(record)

    def get_prompts(self, user_id: Union[str, UUID], post_id: Optional[str] = None) -> list[ImagePromptResponse]:
        """Get image prompts for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        with get_session() as session:
            statement = select(ImagePrompt).where(ImagePrompt.user_id == uid)
            if post_id:
                statement = statement.where(ImagePrompt.post_id == post_id)
            statement = statement.order_by(desc(ImagePrompt.created_at))
            records = session.exec(statement).all()
            return [self._record_to_response(r) for r in records]

    def get_latest_prompt(self, user_id: Union[str, UUID], post_id: str) -> Optional[ImagePromptResponse]:
        """Get the latest prompt for a post."""
        uid = normalize_user_id(user_id)
        if not uid:
            return None
        with get_session() as session:
            statement = (
                select(ImagePrompt)
                .where(ImagePrompt.user_id == uid, ImagePrompt.post_id == post_id)
                .order_by(desc(ImagePrompt.version))
            )
            record = session.exec(statement).first()
            if not record:
                return None
            return self._record_to_response(record)

    def delete_prompt(self, prompt_id: Union[str, UUID]) -> None:
        """Delete an image prompt."""
        pid = coerce_uuid(prompt_id)
        if not pid:
            raise ValueError("Invalid prompt_id")
        with get_session() as session:
            record = session.get(ImagePrompt, pid)
            if not record:
                return
            session.delete(record)
            session.commit()

    def get_scenes_for_user(self, user_id: Union[str, UUID]) -> dict:
        """Get all available scenes from database, grouped by sentiment.

        Args:
            user_id: User ID (required for multi-tenancy)
        """
        result = {}
        for sentiment in ["SUCCESS", "FAILURE", "UNRESOLVED"]:
            db_scenes = self.config_service.get_scenes(user_id, sentiment)
            result[sentiment] = [
                {"code": s["code"], "name": s["name"], "desc": s["description"]}
                for s in db_scenes
            ]
        return result

    def get_poses_for_user(self, user_id: Union[str, UUID]) -> dict:
        """Get all available poses from database, grouped by sentiment.

        Args:
            user_id: User ID (required for multi-tenancy)
        """
        result = {}
        for sentiment in ["SUCCESS", "FAILURE", "UNRESOLVED"]:
            db_poses = self.config_service.get_poses(user_id, sentiment)
            result[sentiment] = [
                {"code": p["code"], "description": p["description"]}
                for p in db_poses
            ]
        return result

    def get_outfits_for_user(self, user_id: Union[str, UUID]) -> list:
        """Get all available outfits from database.

        Args:
            user_id: User ID (required for multi-tenancy)
        """
        db_outfits = self.config_service.get_outfits(user_id)
        return [{"vest": o["vest"], "shirt": o["shirt"]} for o in db_outfits]

    # Keep static methods for backward compatibility
    @staticmethod
    def get_scenes() -> dict:
        """Get default scenes (deprecated - use get_scenes_for_user)."""
        return DEFAULT_SCENES

    @staticmethod
    def get_poses() -> dict:
        """Get default poses (deprecated - use get_poses_for_user)."""
        return DEFAULT_POSES

    @staticmethod
    def get_outfits() -> list:
        """Get default outfits (deprecated - use get_outfits_for_user)."""
        return DEFAULT_OUTFITS
