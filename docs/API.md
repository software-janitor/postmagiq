# API Reference

Base URL: `http://localhost:8000`

## Authentication

### Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

Response:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

### Using Tokens

Include the access token in all authenticated requests:

```http
GET /api/v1/...
Authorization: Bearer eyJ...
```

## Workspaces

### List Workspaces

```http
GET /api/v1/workspaces
Authorization: Bearer <token>
```

Response:
```json
{
  "workspaces": [
    {
      "id": "uuid",
      "name": "My Workspace",
      "slug": "my-workspace",
      "role": "owner"
    }
  ]
}
```

### Create Workspace

```http
POST /api/v1/workspaces
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Workspace",
  "slug": "new-workspace"
}
```

### Get Workspace

```http
GET /api/v1/w/{workspace_id}
Authorization: Bearer <token>
```

## Workspace Members

### List Members

```http
GET /api/v1/w/{workspace_id}/members
Authorization: Bearer <token>
```

Response:
```json
{
  "members": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "owner",
      "joined_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Invite Member

```http
POST /api/v1/w/{workspace_id}/invites
Authorization: Bearer <token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "role": "editor"
}
```

Roles: `admin`, `editor`, `viewer`

### Update Member Role

```http
PATCH /api/v1/w/{workspace_id}/members/{member_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "admin"
}
```

### Remove Member

```http
DELETE /api/v1/w/{workspace_id}/members/{member_id}
Authorization: Bearer <token>
```

## Posts

### List Posts

```http
GET /api/v1/w/{workspace_id}/posts
Authorization: Bearer <token>
```

Query parameters:
- `status` - Filter by status (draft, published, etc.)
- `limit` - Max results (default: 50)
- `offset` - Pagination offset

### Get Post

```http
GET /api/v1/w/{workspace_id}/posts/{post_id}
Authorization: Bearer <token>
```

### Create Post

```http
POST /api/v1/w/{workspace_id}/posts
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "My Post",
  "content": "Post content...",
  "chapter_id": "uuid"
}
```

### Update Post

```http
PATCH /api/v1/w/{workspace_id}/posts/{post_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Updated content..."
}
```

## Workflow

### Run Workflow

```http
POST /api/v1/w/{workspace_id}/workflow
Authorization: Bearer <token>
Content-Type: application/json

{
  "story_name": "post_03",
  "input_content": "Raw story content..."
}
```

Response:
```json
{
  "run_id": "uuid",
  "status": "running"
}
```

### Get Workflow Status

```http
GET /api/v1/w/{workspace_id}/workflow/{run_id}
Authorization: Bearer <token>
```

Response:
```json
{
  "run_id": "uuid",
  "status": "completed",
  "current_state": "done",
  "result": {
    "post_id": "uuid",
    "content": "Generated content..."
  }
}
```

## Billing

### Get Current Subscription

```http
GET /api/v1/w/{workspace_id}/billing/subscription
Authorization: Bearer <token>
```

Response:
```json
{
  "tier": {
    "name": "Individual",
    "slug": "individual",
    "price_monthly": 29.00,
    "posts_per_month": 50
  },
  "status": "active",
  "current_period_end": "2024-02-15T00:00:00Z",
  "usage": {
    "posts_created": 15,
    "posts_limit": 50
  }
}
```

### List Subscription Tiers

```http
GET /api/v1/billing/tiers
Authorization: Bearer <token>
```

### Create Checkout Session

```http
POST /api/v1/w/{workspace_id}/billing/checkout
Authorization: Bearer <token>
Content-Type: application/json

{
  "tier_slug": "team",
  "billing_period": "monthly"
}
```

Response:
```json
{
  "checkout_url": "https://checkout.stripe.com/..."
}
```

## Personas

### List Personas

```http
GET /workflow-personas
Authorization: Bearer <token>
```

Response:
```json
{
  "personas": [
    {
      "id": "writer",
      "name": "Writer",
      "description": "Drafting agent...",
      "is_default": true
    }
  ]
}
```

Note: System personas are only visible to the SaaS owner.

### Get Persona

```http
GET /workflow-personas/{slug}
Authorization: Bearer <token>
```

### Update Persona

```http
PUT /workflow-personas/{slug}
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Updated persona prompt..."
}
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized

```json
{
  "detail": "Missing authentication credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Missing required scope: content:write"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/*` | 10/minute |
| `/api/v1/*` | 100/minute |
| `/workflow` | 10/minute |

When rate limited, response includes:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

## Webhooks (Stripe)

```http
POST /billing/webhook
Stripe-Signature: t=...,v1=...

{
  "type": "checkout.session.completed",
  "data": { ... }
}
```

Handled events:
- `checkout.session.completed` - Subscription created
- `invoice.paid` - Monthly renewal
- `customer.subscription.deleted` - Subscription canceled
