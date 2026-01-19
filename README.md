# Workflow Orchestrator

Multi-tenant SaaS platform for AI-powered LinkedIn content creation.

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL (via Docker)

### Fresh Install

```bash
# 1. Install dependencies
make setup

# 2. Start everything (database, migrations, services)
make dev
```

This starts PostgreSQL, runs migrations (which seed all initial data), then launches all services.

The app will be available at:
- **API**: http://localhost:8000
- **GUI**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator

# JWT
JWT_SECRET=your-secret-key-change-in-production

# Email (optional - logs to console if not set)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
SMTP_FROM=noreply@example.com

# Stripe (optional - for billing)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design.

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    React + TypeScript                        │
│                      (gui/ folder)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
│                   FastAPI + SQLModel                         │
│                     (api/ folder)                            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │  Workflow       │  │   LLM APIs      │
│   + PgBouncer   │  │  Runner         │  │  Claude/Gemini  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| API | `api/` | FastAPI REST endpoints, auth, services |
| Runner | `runner/` | Workflow execution, state machine, agents |
| GUI | `gui/` | React frontend with TypeScript |
| Database | `runner/db/` | SQLModel models, Alembic migrations |

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development guidelines.

### Common Commands

```bash
# Development
make dev              # Start all services (Docker) - includes DB + migrations
make dev-local        # Start API + GUI locally (requires db-up first)
make dev-stop         # Stop servers
make restart          # Restart servers

# Database
make db-up            # Start PostgreSQL only
make db-down          # Stop PostgreSQL
make db-migrate       # Run migrations manually
make db-rollback      # Rollback last migration
make db-shell         # PostgreSQL CLI

# Testing
make test             # Run unit tests
make test-int         # Run integration tests
make coverage         # Generate coverage report

# Personas
make seed-personas    # Update system personas from prompts/
```

## Project Structure

```
orchestrator/
├── api/                    # FastAPI application
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   ├── auth/               # Authentication (JWT, RBAC)
│   └── main.py             # App entry point
├── runner/                 # Workflow engine
│   ├── agents/             # LLM agent implementations
│   ├── db/                 # Database models & migrations
│   ├── content/            # Content repositories
│   └── state_machine.py    # Workflow state machine
├── gui/                    # React frontend
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Shared components
│   │   ├── stores/         # Zustand state stores
│   │   └── api/            # API client
│   └── package.json
├── prompts/                # AI persona templates
├── scripts/                # Utility scripts
├── tests/                  # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker-compose.yml      # Docker services
├── Makefile                # Development commands
└── README.md               # This file
```

## Multi-Tenancy

The platform supports multi-tenant workspaces:

- **Users** belong to **Workspaces**
- **Workspaces** have **Subscriptions** (Free, Individual, Team, Agency)
- All content is scoped to workspaces
- Billing is per-workspace

### User Roles

| Role | Scope | Description |
|------|-------|-------------|
| `owner` | System | SaaS owner, full access |
| `admin` | System | Extended access (future) |
| `user` | System | Regular user |

### Workspace Roles

| Role | Scope | Permissions |
|------|-------|-------------|
| `owner` | Workspace | Full control, billing |
| `admin` | Workspace | Manage members, settings |
| `editor` | Workspace | Create/edit content |
| `viewer` | Workspace | Read-only access |

## Subscription Tiers

| Tier | Price | Posts/Month | Features |
|------|-------|-------------|----------|
| Free | $0 | 5 | Basic features |
| Individual | $29/mo | 50 | Full features |
| Team | $99/mo | 200 | Team collaboration |
| Agency | $249/mo | Unlimited | White-label, API |

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /auth/register` | Register new user |
| `POST /auth/login` | Login, get JWT |
| `GET /api/v1/w/{workspace}/posts` | List posts |
| `POST /api/v1/w/{workspace}/workflow` | Run workflow |
| `GET /api/v1/w/{workspace}/members` | List members |

## License

Proprietary - All rights reserved.
