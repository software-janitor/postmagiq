"""API routes for workflow personas.

OWNER-ONLY: These are internal backend configuration endpoints.
Regular users should not have access to workflow personas.
"""

from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sqlmodel import select

from api.auth.dependencies import CurrentUser, require_owner_role
from runner.content.repository import WorkflowPersonaRepository
from runner.db.engine import get_session
from runner.db.models import WorkflowPersona, UserRole

router = APIRouter()


class WorkflowPersonaUpdate(BaseModel):
    """Request to update a workflow persona."""
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    model_tier: Optional[str] = None  # "writer", "auditor", or "coder"


# =============================================================================
# Frontend-compatible endpoints (match old /personas API format)
# =============================================================================

class PersonaListItem(BaseModel):
    """Persona list item for frontend compatibility."""
    id: str  # slug as ID
    name: str
    description: str
    filename: str  # Generated from slug
    exists: bool = True
    is_default: bool  # Maps to is_system


class PersonaDetail(BaseModel):
    """Persona detail for frontend compatibility."""
    id: str  # slug
    name: str
    description: str
    content: str
    model_tier: Optional[str] = None  # "writer", "auditor", or "coder"


class PersonaCreateRequest(BaseModel):
    """Frontend request to create persona."""
    id: str  # slug
    name: str
    description: str = ""
    model_tier: str = "writer"  # Default to writer tier


def _get_persona_by_slug(session, user_id: UUID, slug: str) -> Optional[WorkflowPersona]:
    """Fetch persona by slug, checking user-specific then system."""
    repo = WorkflowPersonaRepository(session)
    persona = repo.get_by_slug(user_id, slug)
    if persona:
        return persona
    return session.exec(
        select(WorkflowPersona).where(
            WorkflowPersona.is_system == True,
            WorkflowPersona.slug == slug,
        )
    ).first()


@router.get("/workflow-personas")
def list_personas(
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
) -> dict:
    """List all personas (frontend-compatible format).

    System personas are only visible to the SaaS owner.
    """
    uid = current_user.user_id
    is_owner = current_user.user.role == UserRole.owner

    with get_session() as session:
        repo = WorkflowPersonaRepository(session)
        personas = repo.list_by_user(uid)

        # Only include system personas for SaaS owner
        if is_owner:
            system_personas = repo.list_system_personas()
            by_slug = {p.slug: p for p in system_personas}
            for persona in personas:
                by_slug[persona.slug] = persona
        else:
            by_slug = {p.slug: p for p in personas}

        ordered = sorted(
            by_slug.values(),
            key=lambda p: (not p.is_system, p.name),
        )

        return {
            "personas": [
                PersonaListItem(
                    id=p.slug,
                    name=p.name,
                    description=p.description or "",
                    filename=f"{p.slug.replace('-', '_')}_persona.md",
                    exists=True,
                    is_default=p.is_system,
                )
                for p in ordered
            ]
        }


@router.get("/workflow-personas/{slug}")
def get_persona_by_slug(
    slug: str,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
) -> PersonaDetail:
    """Get persona by slug (frontend-compatible format).

    System personas are only accessible to the SaaS owner.
    """
    uid = current_user.user_id
    is_owner = current_user.user.role == UserRole.owner

    with get_session() as session:
        persona = _get_persona_by_slug(session, uid, slug)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")

        # Non-owners cannot access system personas
        if persona.is_system and not is_owner:
            raise HTTPException(status_code=404, detail="Persona not found")

        return PersonaDetail(
            id=persona.slug,
            name=persona.name,
            description=persona.description or "",
            content=persona.content,
            model_tier=persona.model_tier,
        )


@router.put("/workflow-personas/{slug}")
def update_persona_by_slug(
    slug: str,
    request: WorkflowPersonaUpdate,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
) -> PersonaDetail:
    """Update persona by slug (frontend-compatible format).

    System personas can only be edited by the SaaS owner.
    """
    uid = current_user.user_id
    is_owner = current_user.user.role == UserRole.owner

    with get_session() as session:
        persona = _get_persona_by_slug(session, uid, slug)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")

        # Non-owners cannot edit system personas
        if persona.is_system and not is_owner:
            raise HTTPException(status_code=403, detail="Cannot edit system personas")

        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        for key, value in updates.items():
            if hasattr(persona, key):
                setattr(persona, key, value)
        if updates:
            session.add(persona)
            session.commit()
            session.refresh(persona)

        return PersonaDetail(
            id=persona.slug,
            name=persona.name,
            description=persona.description or "",
            content=persona.content,
            model_tier=persona.model_tier,
        )


@router.post("/workflow-personas")
def create_persona(
    request: PersonaCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
) -> PersonaDetail:
    """Create a new persona (frontend-compatible format)."""
    uid = current_user.user_id
    with get_session() as session:
        existing = _get_persona_by_slug(session, uid, request.id)
        if existing:
            raise HTTPException(status_code=400, detail="Persona with this ID already exists")

        record = WorkflowPersona(
            user_id=uid,
            name=request.name,
            slug=request.id,
            description=request.description,
            content="",
            is_system=False,
            model_tier=request.model_tier,
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        return PersonaDetail(
            id=record.slug,
            name=record.name,
            description=record.description or "",
            content=record.content,
            model_tier=record.model_tier,
        )


@router.delete("/workflow-personas/{slug}")
def delete_persona_by_slug(
    slug: str,
    current_user: Annotated[CurrentUser, Depends(require_owner_role())],
) -> dict:
    """Delete persona by slug (frontend-compatible format)."""
    uid = current_user.user_id
    with get_session() as session:
        persona = _get_persona_by_slug(session, uid, slug)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        if persona.is_system:
            raise HTTPException(status_code=403, detail="Cannot delete system personas")
        session.delete(persona)
        session.commit()
        return {"deleted": True}


# =============================================================================
# REMOVED: Legacy user_id routes (security remediation)
# =============================================================================
# The following routes were removed per SECURITY_REMEDIATION_TRACKER.md Phase 4:
# - GET /users/{user_id}/workflow-personas
# - GET /users/{user_id}/workflow-personas/by-slug/{slug}
# - PUT /workflow-personas/by-id/{persona_id}
#
# Rationale: These routes exposed unnecessary user_id path parameters.
# Use the frontend-compatible routes instead:
# - GET /workflow-personas (list all)
# - GET /workflow-personas/{slug} (get by slug)
# - PUT /workflow-personas/{slug} (update by slug)


