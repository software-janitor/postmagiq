# Plan: Direct Publishing to LinkedIn, X, and Threads

> Add "Publish Now" button to post directly from Postmagiq. All platforms have free APIs.

---

## Goal

Users generate content → click "Publish to LinkedIn" → done. No copy-paste.

---

## Platform Priority

| Priority | Platform | Why |
|----------|----------|-----|
| 1 | LinkedIn | Target users are B2B thought leaders |
| 2 | X (Twitter) | Broad reach, easy API |
| 3 | Threads | Growing platform, same content works |

---

## Phase 1: LinkedIn Publishing

### API Details

| Item | Value |
|------|-------|
| API | LinkedIn API v2 (ugcPosts endpoint) |
| Auth | OAuth 2.0 (3-legged flow) |
| Cost | **Free** |
| Scopes | `w_member_social`, `openid`, `profile`, `email` |
| Token expiry | 60 days (refresh available) |
| Docs | [LinkedIn Auth Flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow) |

### Implementation

**Backend:**

```python
# api/routes/v1/publishing.py

@router.post("/publish/linkedin")
async def publish_to_linkedin(
    request: PublishRequest,
    ctx: WorkspaceCtx,
):
    """Publish content to LinkedIn."""
    # Get user's LinkedIn token
    # POST to ugcPosts endpoint
    # Return post URL
```

**Database:**

```python
# runner/db/models/social_connection.py

class SocialConnection(UUIDModel, table=True):
    """OAuth tokens for social platforms."""
    __tablename__ = "social_connections"

    user_id: UUID = Field(foreign_key="users.id")
    platform: str  # "linkedin", "x", "threads"
    access_token: str  # encrypted
    refresh_token: Optional[str]
    expires_at: datetime
    platform_user_id: str  # LinkedIn URN, X user ID, etc.
    platform_username: str  # For display
    scopes: str  # Comma-separated
    created_at: datetime
    updated_at: datetime
```

**Frontend:**

```tsx
// gui/src/components/PublishButton.tsx

interface PublishButtonProps {
  content: string
  platform: 'linkedin' | 'x' | 'threads'
  onSuccess: (postUrl: string) => void
}

// Shows "Connect LinkedIn" if not connected
// Shows "Publish to LinkedIn" if connected
```

### OAuth Flow

```
1. User clicks "Connect LinkedIn"
2. Redirect to: https://www.linkedin.com/oauth/v2/authorization
   - response_type=code
   - client_id={LINKEDIN_CLIENT_ID}
   - redirect_uri={API_URL}/v1/auth/linkedin/callback
   - scope=openid profile email w_member_social
   - state={random_state}

3. User authorizes
4. LinkedIn redirects to callback with code
5. Backend exchanges code for tokens
6. Store tokens in social_connections table
7. Redirect user back to app
```

### LinkedIn Post Format

```python
# LinkedIn ugcPost payload
{
    "author": "urn:li:person:{person_id}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": content
            },
            "shareMediaCategory": "NONE"  # or "IMAGE" with media
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}
```

### Files to Create

| File | Purpose |
|------|---------|
| `api/routes/v1/publishing.py` | Publish endpoints |
| `api/routes/v1/social_auth.py` | OAuth callback handlers |
| `api/services/linkedin_service.py` | LinkedIn API client |
| `runner/db/models/social_connection.py` | Token storage |
| `runner/db/migrations/versions/xxx_social_connections.py` | Migration |
| `gui/src/components/PublishButton.tsx` | Publish UI |
| `gui/src/components/ConnectSocialButton.tsx` | OAuth trigger |
| `gui/src/pages/SocialConnections.tsx` | Manage connections |

---

## Phase 2: X (Twitter) Publishing

### API Details

| Item | Value |
|------|-------|
| API | X API v2 (POST /2/tweets) |
| Auth | OAuth 1.0a (for posting) |
| Cost | **Free tier: 1,500 posts/month** |
| Scopes | `tweet.read`, `tweet.write`, `users.read` |
| Docs | [X Create Post](https://docs.x.com/x-api/posts/create-post) |

### Implementation

```python
# api/services/x_service.py

import tweepy

class XService:
    def __init__(self, access_token: str, access_secret: str):
        auth = tweepy.OAuth1UserHandler(
            X_API_KEY,
            X_API_SECRET,
            access_token,
            access_secret
        )
        self.client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=access_token,
            access_token_secret=access_secret,
        )

    def post(self, text: str) -> str:
        """Post tweet, return tweet URL."""
        response = self.client.create_tweet(text=text)
        tweet_id = response.data["id"]
        return f"https://x.com/i/status/{tweet_id}"
```

### OAuth 1.0a Flow

```
1. User clicks "Connect X"
2. POST /oauth/request_token
3. Redirect to: https://api.twitter.com/oauth/authorize
4. User authorizes
5. X redirects with oauth_token, oauth_verifier
6. POST /oauth/access_token to exchange
7. Store tokens
```

### Character Limit Handling

```tsx
// X has 280 char limit (4000 for Premium)
// Show warning if content > 280
// Offer to truncate or thread
```

---

## Phase 3: Threads Publishing

### API Details

| Item | Value |
|------|-------|
| API | Threads API (Meta Graph API) |
| Auth | OAuth 2.0 via Instagram |
| Cost | **Free** |
| Scopes | `threads_basic`, `threads_content_publish` |
| Docs | [Threads API](https://developers.facebook.com/docs/threads) |

### Two-Step Publishing

```python
# api/services/threads_service.py

class ThreadsService:
    def post(self, user_id: str, text: str, access_token: str) -> str:
        """Threads requires two API calls."""

        # Step 1: Create media container
        container = requests.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads",
            params={
                "media_type": "TEXT",
                "text": text,
                "access_token": access_token,
            }
        ).json()

        container_id = container["id"]

        # Step 2: Publish
        result = requests.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
            params={
                "creation_id": container_id,
                "access_token": access_token,
            }
        ).json()

        return f"https://threads.net/@{username}/post/{result['id']}"
```

---

## UI/UX Design

### Finished Posts Page

```
┌─────────────────────────────────────────────────────┐
│ Your LinkedIn Post                                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Generated content here...]                         │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ 📋 Copy      │ │ in Publish   │ │ 𝕏 Publish    │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ │
│                  ┌──────────────┐                   │
│                  │ 🧵 Publish   │                   │
│                  └──────────────┘                   │
└─────────────────────────────────────────────────────┘
```

### Settings: Connected Accounts

```
┌─────────────────────────────────────────────────────┐
│ Connected Accounts                                   │
├─────────────────────────────────────────────────────┤
│ LinkedIn    ✓ Connected as @johndoe   [Disconnect] │
│ X           ○ Not connected           [Connect]    │
│ Threads     ○ Not connected           [Connect]    │
└─────────────────────────────────────────────────────┘
```

---

## Database Migration

```python
# runner/db/migrations/versions/xxx_social_connections.py

def upgrade():
    op.create_table(
        "social_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("access_token", sa.Text, nullable=False),  # Encrypt this
        sa.Column("refresh_token", sa.Text),
        sa.Column("expires_at", sa.DateTime),
        sa.Column("platform_user_id", sa.String(255), nullable=False),
        sa.Column("platform_username", sa.String(255)),
        sa.Column("scopes", sa.Text),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime, default=datetime.utcnow),
    )

    # Unique constraint: one connection per user per platform
    op.create_unique_constraint(
        "uq_social_connections_user_platform",
        "social_connections",
        ["user_id", "platform"]
    )
```

---

## Environment Variables

```bash
# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=

# X (Twitter)
X_API_KEY=
X_API_SECRET=

# Threads (Meta)
THREADS_APP_ID=
THREADS_APP_SECRET=
```

---

## API Endpoints

```
# OAuth
GET  /v1/auth/linkedin/connect     → Redirect to LinkedIn OAuth
GET  /v1/auth/linkedin/callback    → Handle callback, store token
GET  /v1/auth/x/connect            → Redirect to X OAuth
GET  /v1/auth/x/callback           → Handle callback
GET  /v1/auth/threads/connect      → Redirect to Threads OAuth
GET  /v1/auth/threads/callback     → Handle callback

# Connections
GET  /v1/social/connections        → List user's connected accounts
DELETE /v1/social/connections/{id} → Disconnect account

# Publishing
POST /v1/publish/linkedin          → { content, post_id? }
POST /v1/publish/x                 → { content, post_id? }
POST /v1/publish/threads           → { content, post_id? }
```

---

## Error Handling

| Error | User Message |
|-------|--------------|
| Token expired | "Your LinkedIn connection expired. Please reconnect." |
| Rate limited | "Too many posts. Please wait and try again." |
| Content too long | "This post exceeds X's 280 character limit." |
| API error | "Failed to publish. Please try again or copy manually." |
| Account suspended | "Your {platform} account may have restrictions." |

---

## Security Considerations

1. **Encrypt tokens at rest** - Use Fernet or similar
2. **HTTPS only** - OAuth callbacks must be HTTPS
3. **State parameter** - Prevent CSRF in OAuth flow
4. **Scope minimization** - Only request needed scopes
5. **Token refresh** - Handle expiry gracefully

---

## Testing Checklist

- [ ] LinkedIn OAuth flow works end-to-end
- [ ] LinkedIn post appears on user's profile
- [ ] X OAuth flow works
- [ ] X tweet posts successfully
- [ ] Threads OAuth flow works
- [ ] Threads post appears
- [ ] Token refresh works for LinkedIn
- [ ] Disconnect removes tokens
- [ ] Error messages are user-friendly
- [ ] Character limits enforced for X
- [ ] Multiple accounts can be connected

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Database + models | 2 hours |
| LinkedIn OAuth + publish | 4-6 hours |
| X OAuth + publish | 3-4 hours |
| Threads OAuth + publish | 3-4 hours |
| Frontend UI | 4-5 hours |
| Testing | 2-3 hours |
| **Total** | **18-24 hours** |

---

## Launch Priority

1. **LinkedIn only** for soft launch (1 week)
2. Add X in week 2
3. Add Threads in week 3

This lets you ship faster and validate the core flow.
