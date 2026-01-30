"""OAuth routes for social media platform connections.

Handles OAuth flows for LinkedIn, X (Twitter), and Threads.
"""

import secrets
from datetime import datetime, timedelta
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from api.routes.v1.dependencies import WorkspaceContext, get_workspace_context
from runner.db.engine import get_session_dependency
from runner.db.models import (
    SocialConnection,
    SocialConnectionRead,
    SocialPlatform,
)
from api.services.social_service import (
    linkedin_service,
    x_service,
    threads_service,
)

router = APIRouter(prefix="/social", tags=["social"])


class OAuthState(BaseModel):
    """State stored during OAuth flow."""

    workspace_id: str
    user_id: str
    platform: str
    nonce: str


# In-memory state store (use Redis in production)
_oauth_states: dict[str, OAuthState] = {}


def _create_oauth_state(
    workspace_id: UUID, user_id: UUID, platform: SocialPlatform
) -> str:
    """Create and store OAuth state parameter."""
    nonce = secrets.token_urlsafe(32)
    state = OAuthState(
        workspace_id=str(workspace_id),
        user_id=str(user_id),
        platform=platform.value,
        nonce=nonce,
    )
    _oauth_states[nonce] = state
    return nonce


def _verify_oauth_state(state: str) -> Optional[OAuthState]:
    """Verify and consume OAuth state parameter."""
    return _oauth_states.pop(state, None)


# =============================================================================
# List/Delete Connections
# =============================================================================


@router.get(
    "/w/{workspace_id}/connections",
    response_model=list[SocialConnectionRead],
)
async def list_connections(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> list[SocialConnectionRead]:
    """List all social connections for the workspace."""
    statement = select(SocialConnection).where(
        SocialConnection.workspace_id == ctx.workspace_id,
        SocialConnection.user_id == ctx.user_id,
    )
    connections = session.exec(statement).all()
    return [SocialConnectionRead.model_validate(c) for c in connections]


@router.delete("/w/{workspace_id}/connections/{connection_id}")
async def delete_connection(
    connection_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> dict:
    """Delete a social connection."""
    connection = session.get(SocialConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    if connection.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if connection.user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    session.delete(connection)
    session.commit()
    return {"status": "disconnected"}


# =============================================================================
# LinkedIn OAuth
# =============================================================================


@router.get("/w/{workspace_id}/connect/linkedin")
async def connect_linkedin(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
) -> RedirectResponse:
    """Initiate LinkedIn OAuth flow."""
    state = _create_oauth_state(ctx.workspace_id, ctx.user_id, SocialPlatform.linkedin)
    auth_url = linkedin_service.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/callback/linkedin")
async def linkedin_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: Session = Depends(get_session_dependency),
) -> RedirectResponse:
    """Handle LinkedIn OAuth callback."""
    oauth_state = _verify_oauth_state(state)
    if not oauth_state:
        return RedirectResponse(url="/settings?error=invalid_state")

    try:
        # Exchange code for tokens
        tokens = await linkedin_service.exchange_code(code)

        # Get user profile
        profile = await linkedin_service.get_profile(tokens["access_token"])

        # Check for existing connection
        statement = select(SocialConnection).where(
            SocialConnection.user_id == UUID(oauth_state.user_id),
            SocialConnection.workspace_id == UUID(oauth_state.workspace_id),
            SocialConnection.platform == SocialPlatform.linkedin,
        )
        existing = session.exec(statement).first()

        if existing:
            # Update existing connection
            existing.access_token = tokens["access_token"]
            existing.refresh_token = tokens.get("refresh_token")
            existing.expires_at = datetime.utcnow() + timedelta(
                seconds=tokens.get("expires_in", 5184000)
            )
            existing.platform_user_id = profile["id"]
            existing.platform_username = profile["username"]
            existing.platform_name = profile.get("name")
            existing.updated_at = datetime.utcnow()
        else:
            # Create new connection
            connection = SocialConnection(
                user_id=UUID(oauth_state.user_id),
                workspace_id=UUID(oauth_state.workspace_id),
                platform=SocialPlatform.linkedin,
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                expires_at=datetime.utcnow()
                + timedelta(seconds=tokens.get("expires_in", 5184000)),
                platform_user_id=profile["id"],
                platform_username=profile["username"],
                platform_name=profile.get("name"),
                scopes=tokens.get("scope"),
            )
            session.add(connection)

        session.commit()
        return RedirectResponse(url="/settings?connected=linkedin")

    except Exception as e:
        return RedirectResponse(url=f"/settings?error={str(e)}")


# =============================================================================
# X (Twitter) OAuth
# =============================================================================


@router.get("/w/{workspace_id}/connect/x")
async def connect_x(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
) -> RedirectResponse:
    """Initiate X OAuth 1.0a flow."""
    state = _create_oauth_state(ctx.workspace_id, ctx.user_id, SocialPlatform.x)
    auth_url, request_token, request_secret = await x_service.get_authorization_url(
        state
    )
    # Store request token/secret for callback
    _oauth_states[f"x_token_{state}"] = {
        "token": request_token,
        "secret": request_secret,
    }
    return RedirectResponse(url=auth_url)


@router.get("/callback/x")
async def x_callback(
    oauth_token: str = Query(...),
    oauth_verifier: str = Query(...),
    state: str = Query(None),
    session: Session = Depends(get_session_dependency),
) -> RedirectResponse:
    """Handle X OAuth callback."""
    # For OAuth 1.0a, we need to find the state from the token
    oauth_state = None
    request_secret = None

    for key, value in list(_oauth_states.items()):
        if key.startswith("x_token_") and isinstance(value, dict):
            if value.get("token") == oauth_token:
                state_key = key.replace("x_token_", "")
                oauth_state = _oauth_states.pop(state_key, None)
                request_secret = value.get("secret")
                del _oauth_states[key]
                break

    if not oauth_state or not request_secret:
        return RedirectResponse(url="/settings?error=invalid_state")

    try:
        # Exchange for access token
        tokens = await x_service.exchange_code(
            oauth_token, request_secret, oauth_verifier
        )

        # Get user profile
        profile = await x_service.get_profile(
            tokens["access_token"], tokens["access_token_secret"]
        )

        # Check for existing connection
        statement = select(SocialConnection).where(
            SocialConnection.user_id == UUID(oauth_state.user_id),
            SocialConnection.workspace_id == UUID(oauth_state.workspace_id),
            SocialConnection.platform == SocialPlatform.x,
        )
        existing = session.exec(statement).first()

        if existing:
            existing.access_token = tokens["access_token"]
            existing.token_secret = tokens["access_token_secret"]
            existing.platform_user_id = profile["id"]
            existing.platform_username = profile["username"]
            existing.platform_name = profile.get("name")
            existing.updated_at = datetime.utcnow()
        else:
            connection = SocialConnection(
                user_id=UUID(oauth_state.user_id),
                workspace_id=UUID(oauth_state.workspace_id),
                platform=SocialPlatform.x,
                access_token=tokens["access_token"],
                token_secret=tokens["access_token_secret"],
                platform_user_id=profile["id"],
                platform_username=profile["username"],
                platform_name=profile.get("name"),
            )
            session.add(connection)

        session.commit()
        return RedirectResponse(url="/settings?connected=x")

    except Exception as e:
        return RedirectResponse(url=f"/settings?error={str(e)}")


# =============================================================================
# Threads OAuth
# =============================================================================


@router.get("/w/{workspace_id}/connect/threads")
async def connect_threads(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
) -> RedirectResponse:
    """Initiate Threads OAuth flow."""
    state = _create_oauth_state(ctx.workspace_id, ctx.user_id, SocialPlatform.threads)
    auth_url = threads_service.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/callback/threads")
async def threads_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: Session = Depends(get_session_dependency),
) -> RedirectResponse:
    """Handle Threads OAuth callback."""
    oauth_state = _verify_oauth_state(state)
    if not oauth_state:
        return RedirectResponse(url="/settings?error=invalid_state")

    try:
        # Exchange code for tokens
        tokens = await threads_service.exchange_code(code)

        # Get user profile
        profile = await threads_service.get_profile(tokens["access_token"])

        # Check for existing connection
        statement = select(SocialConnection).where(
            SocialConnection.user_id == UUID(oauth_state.user_id),
            SocialConnection.workspace_id == UUID(oauth_state.workspace_id),
            SocialConnection.platform == SocialPlatform.threads,
        )
        existing = session.exec(statement).first()

        if existing:
            existing.access_token = tokens["access_token"]
            existing.expires_at = datetime.utcnow() + timedelta(
                seconds=tokens.get("expires_in", 5184000)
            )
            existing.platform_user_id = profile["id"]
            existing.platform_username = profile["username"]
            existing.platform_name = profile.get("name")
            existing.updated_at = datetime.utcnow()
        else:
            connection = SocialConnection(
                user_id=UUID(oauth_state.user_id),
                workspace_id=UUID(oauth_state.workspace_id),
                platform=SocialPlatform.threads,
                access_token=tokens["access_token"],
                expires_at=datetime.utcnow()
                + timedelta(seconds=tokens.get("expires_in", 5184000)),
                platform_user_id=profile["id"],
                platform_username=profile["username"],
                platform_name=profile.get("name"),
                scopes=tokens.get("scope"),
            )
            session.add(connection)

        session.commit()
        return RedirectResponse(url="/settings?connected=threads")

    except Exception as e:
        return RedirectResponse(url=f"/settings?error={str(e)}")
