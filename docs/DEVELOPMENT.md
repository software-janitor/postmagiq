# Development Guide

## Getting Started

### Prerequisites

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Node.js 18+**
   ```bash
   node --version
   npm --version
   ```

3. **Docker & Docker Compose**
   ```bash
   docker --version
   docker compose version
   ```

4. **GitHub CLI** (optional, for PRs)
   ```bash
   gh --version
   # Install: brew install gh (macOS)
   ```

### Initial Setup

```bash
# Clone repository
git clone git@github.com:software-janitor/linkedin_articles.git
cd linkedin_articles/orchestrator

# Install all dependencies
make setup

# Start everything (Docker)
make dev
```

This single command:
1. Starts PostgreSQL and PgBouncer in Docker
2. Runs all migrations (creates tables + seeds data)
3. Starts all services (api, gui, ollama, redis)

## Development Workflow

### Daily Workflow

```bash
# Start all services (recommended - uses Docker)
make dev

# Or for local development (runs API and GUI on host machine)
make db-up       # Start database first
make dev-local   # Start API + GUI locally

# In another terminal, run tests while developing
make test
```

### Making Changes

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes**

3. **Run tests**
   ```bash
   make test
   ```

4. **Commit and push**
   ```bash
   git add -A
   git commit -m "Description of changes"
   git push -u origin feature/your-feature
   ```

5. **Create PR**
   ```bash
   make pr TITLE="Your PR title"
   ```

## Project Structure

### API (api/)

```
api/
├── routes/           # API endpoints
│   ├── v1/           # Versioned routes
│   │   ├── workspaces.py
│   │   ├── posts.py
│   │   └── members.py
│   ├── auth.py       # Authentication
│   └── billing.py    # Stripe integration
├── services/         # Business logic
├── auth/             # JWT, RBAC
└── main.py           # App entry
```

**Adding a new endpoint:**

```python
# api/routes/v1/example.py
from fastapi import APIRouter, Depends
from api.auth.dependencies import get_current_user, CurrentUser

router = APIRouter()

@router.get("/example")
def get_example(
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    return {"message": "Hello"}
```

Register in `api/main.py`:
```python
from api.routes.v1 import example
app.include_router(example.router, prefix="/api/v1", tags=["example"])
```

### Database (runner/db/)

**Adding a new model:**

```python
# runner/db/models/example.py
from sqlmodel import SQLModel, Field
from runner.db.models.base import UUIDModel, TimestampMixin

class Example(UUIDModel, TimestampMixin, table=True):
    __tablename__ = "examples"

    name: str
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
```

Export in `runner/db/models/__init__.py`:
```python
from runner.db.models.example import Example
```

**Creating a migration:**

```bash
make db-revision MSG="add examples table"
```

This creates a new file in `runner/db/migrations/versions/`. Review it, then:

```bash
make db-migrate
```

### Frontend (gui/)

```
gui/src/
├── api/              # API client
├── components/       # Shared components
├── pages/            # Route pages
├── stores/           # Zustand stores
└── App.tsx           # Router
```

**Adding a new page:**

```typescript
// gui/src/pages/Example.tsx
export function Example() {
  return <div>Example Page</div>
}
```

Add route in `gui/src/App.tsx`:
```typescript
import { Example } from './pages/Example'

// In routes:
<Route path="/example" element={<Example />} />
```

## Testing

### Running Tests

```bash
# All unit tests
make test

# Specific file
make test-file FILE=tests/unit/test_example.py

# Integration tests
make test-int

# E2E tests (costs money - uses real APIs)
make test-e2e

# Coverage report
make coverage
```

### Writing Tests

```python
# tests/unit/test_example.py
import pytest
from unittest.mock import MagicMock

class TestExample:
    def test_basic(self):
        result = some_function()
        assert result == expected

    def test_with_mock(self):
        mock_repo = MagicMock()
        mock_repo.get.return_value = SomeModel(...)

        service = SomeService(repo=mock_repo)
        result = service.do_something()

        mock_repo.get.assert_called_once()
```

## Database

### Migrations

```bash
# View current migration
make db-current

# View history
make db-history

# Create new migration
make db-revision MSG="description"

# Apply migrations
make db-migrate

# Rollback one migration
make db-rollback
```

### Direct Access

```bash
# PostgreSQL CLI
make db-shell

# Example queries:
SELECT * FROM users LIMIT 10;
SELECT * FROM workspaces WHERE owner_id = '...';
```

## Authentication

### JWT Flow

1. User logs in: `POST /auth/login`
2. Server returns `access_token` and `refresh_token`
3. Client stores tokens
4. Requests include `Authorization: Bearer <access_token>`
5. When access token expires, use `POST /auth/refresh`

### Testing Authenticated Endpoints

```python
# In tests
from api.auth.jwt import create_access_token

token = create_access_token({"sub": str(user.id)})
headers = {"Authorization": f"Bearer {token}"}

response = client.get("/api/v1/...", headers=headers)
```

## Common Tasks

### Adding a New Feature

1. **Plan the data model** - What tables/columns needed?
2. **Create migration** - `make db-revision MSG="..."`
3. **Add SQLModel models** - In `runner/db/models/`
4. **Add repository** - In `runner/content/` if needed
5. **Add service** - In `api/services/`
6. **Add routes** - In `api/routes/`
7. **Write tests** - In `tests/unit/`
8. **Add frontend** - In `gui/src/pages/`

### Debugging

**API Logs:**
```bash
# Watch API logs
make dev  # Logs appear in terminal
```

**Database Queries:**
```python
# Enable SQLAlchemy echo
# In runner/db/engine.py:
engine = create_engine(DATABASE_URL, echo=True)
```

**Frontend:**
- React DevTools browser extension
- Network tab in browser DevTools

### Environment Variables

Required:
```bash
DATABASE_URL=postgresql://user:pass@localhost:6432/db
JWT_SECRET=your-secret-key
```

Optional:
```bash
# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

## Code Style

### Python

- Use type hints
- Follow existing patterns
- Keep functions small
- Write docstrings for public functions

```python
def create_workspace(
    name: str,
    owner_id: UUID,
    slug: Optional[str] = None,
) -> Workspace:
    """Create a new workspace with the given owner.

    Args:
        name: Display name for the workspace
        owner_id: UUID of the owning user
        slug: URL-safe identifier (auto-generated if not provided)

    Returns:
        The created Workspace instance
    """
    ...
```

### TypeScript

- Use TypeScript strictly (no `any`)
- Prefer functional components
- Use hooks for state/effects

```typescript
interface Props {
  workspaceId: string
  onSave: (data: FormData) => Promise<void>
}

export function WorkspaceForm({ workspaceId, onSave }: Props) {
  const [loading, setLoading] = useState(false)
  // ...
}
```

## Troubleshooting

### Database Connection Errors

```bash
# Check if PostgreSQL is running
docker compose ps

# Restart database
make db-down && make db-up

# Check logs
docker compose logs postgres
```

### Migration Errors

```bash
# Check current state
make db-current

# If stuck, check for pending migrations
make db-history

# Force to a specific revision (careful!)
cd runner/db && alembic stamp <revision>
```

### Port Already in Use

```bash
# Find what's using the port
lsof -i :8000
lsof -i :5173

# Kill the process
kill -9 <PID>

# Or use make
make dev-stop
```
