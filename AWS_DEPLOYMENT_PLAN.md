# AWS Deployment Plan for Postmagiq

## Current Architecture Summary

Your application consists of:
- **API**: FastAPI backend (Python 3.11)
- **GUI**: React/Vite frontend (Node 20)
- **Database**: PostgreSQL 16 with pgvector + PgBouncer
- **Cache**: Redis 7
- **LLM Services**: Ollama (local) + external APIs (Anthropic, Google, OpenAI, Groq)
- **Watermark Service**: LaMA ML model (optional, GPU-capable)
- **File Storage**: Workflow artifacts, sessions, drafts

Multi-tenancy ready with workspace isolation and custom domain support.

---

## Recommended AWS Architecture: ECS Fargate

Based on [AWS SaaS Reference Architecture for ECS](https://github.com/aws-samples/saas-reference-architecture-ecs) and the [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/).

```
                                    ┌─────────────────┐
                                    │   Route 53      │
                                    │   (DNS)         │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │  CloudFront     │
                                    │  (CDN + WAF)    │
                                    └────────┬────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     │                       │                       │
            ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
            │   S3 Bucket     │    │   ALB           │    │   S3 Bucket     │
            │   (GUI Static)  │    │   (API LB)      │    │   (Artifacts)   │
            └─────────────────┘    └────────┬────────┘    └─────────────────┘
                                            │
                               ┌────────────┼────────────┐
                               │            │            │
                      ┌────────▼───┐  ┌─────▼─────┐  ┌───▼────────┐
                      │ ECS Fargate│  │ECS Fargate│  │ECS Fargate │
                      │ API (x2+)  │  │ Workers   │  │ Watermark  │
                      └────────┬───┘  └─────┬─────┘  └────────────┘
                               │            │
              ┌────────────────┼────────────┼────────────────┐
              │                │            │                │
     ┌────────▼───────┐  ┌─────▼─────┐  ┌───▼────┐  ┌───────▼───────┐
     │ RDS PostgreSQL │  │ElastiCache│  │Secrets │  │ Parameter     │
     │ (Multi-AZ)     │  │ Redis     │  │Manager │  │ Store         │
     └────────────────┘  └───────────┘  └────────┘  └───────────────┘
```

---

## AWS Services Mapping

| Current Component | AWS Service | Tier |
|-------------------|-------------|------|
| PostgreSQL + PgBouncer | RDS PostgreSQL + RDS Proxy | db.t3.medium → db.r6g.large |
| Redis | ElastiCache Redis | cache.t3.micro → cache.r6g.large |
| API (FastAPI) | ECS Fargate | 0.5 vCPU / 1GB → 2 vCPU / 4GB |
| GUI (React) | S3 + CloudFront | Static hosting |
| Workflow artifacts | S3 | Standard storage |
| Ollama | EC2 GPU or Bedrock | g4dn.xlarge (optional) |
| Watermark Service | ECS Fargate (GPU) | Optional |
| Environment vars | Secrets Manager + Parameter Store | |
| DNS | Route 53 | |
| SSL/TLS | ACM (Certificate Manager) | |
| CDN + WAF | CloudFront + AWS WAF | |
| Monitoring | CloudWatch + X-Ray | |
| CI/CD | CodePipeline + CodeBuild | |

---

## Phase 1: Foundation (VPC + Database)

### 1.1 VPC Setup
- 2 AZs minimum (3 for production)
- Public subnets (ALB, NAT Gateway)
- Private subnets (ECS, RDS, ElastiCache)
- NAT Gateway for outbound traffic

### 1.2 RDS PostgreSQL
```
Engine: PostgreSQL 16
Instance: db.t3.medium (dev) / db.r6g.large (prod)
Storage: 100GB gp3, auto-scaling
Multi-AZ: Yes (prod)
Extensions: pgvector
Backup: 7-day automated
```

### 1.3 RDS Proxy (replaces PgBouncer)
- Connection pooling
- IAM authentication option
- Reduces connection overhead for Fargate

### 1.4 ElastiCache Redis
```
Engine: Redis 7
Node: cache.t3.micro (dev) / cache.r6g.large (prod)
Cluster Mode: Disabled (single node for dev)
Multi-AZ: Yes (prod)
```

---

## Phase 2: Compute (ECS Fargate)

### 2.1 ECS Cluster
- Fargate launch type (serverless containers)
- Capacity providers: FARGATE + FARGATE_SPOT (cost savings)

### 2.2 Task Definitions

**API Service:**
```
CPU: 512 (0.5 vCPU) → 2048 (2 vCPU)
Memory: 1024 MB → 4096 MB
Port: 8000
Health: /api/health
Environment: Secrets Manager refs
```

**Worker Service (optional):**
- For background workflow execution
- Can share same image, different command

### 2.3 Application Load Balancer
- HTTPS termination (ACM certificate)
- Path-based routing: `/api/*` → API service
- Health checks: `/api/health`
- Target group: ECS service

---

## Phase 3: Storage + CDN

### 3.1 S3 Buckets
```
postmagiq-gui-{env}        # Static frontend build
postmagiq-artifacts-{env}  # Workflow drafts, audits, finals
postmagiq-sessions-{env}   # Orchestrator session state
```

### 3.2 CloudFront Distribution
- Origin 1: S3 (GUI static files)
- Origin 2: ALB (API passthrough)
- Behaviors:
  - `/api/*` → ALB origin
  - `/*` → S3 origin
- WAF integration for security

---

## Phase 4: Security + Secrets

### 4.1 Secrets Manager
```
postmagiq/db-credentials     # POSTGRES_PASSWORD
postmagiq/jwt-secret         # JWT_SECRET
postmagiq/stripe             # STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
postmagiq/llm-keys           # ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.
postmagiq/smtp               # SMTP credentials
```

### 4.2 IAM Roles
- ECS Task Execution Role (pull images, secrets)
- ECS Task Role (S3 access, CloudWatch logs)

### 4.3 Security Groups
- ALB: 443 from anywhere
- ECS: 8000 from ALB only
- RDS: 5432 from ECS only
- ElastiCache: 6379 from ECS only

---

## Phase 5: CI/CD Pipeline

### Option A: CodePipeline + CodeBuild
```
Source: GitHub webhook
Build: CodeBuild (Docker image)
Deploy: ECS rolling update
```

### Option B: GitHub Actions
```yaml
# .github/workflows/deploy.yml
- Build Docker image
- Push to ECR
- Update ECS service
```

---

## Phase 6: Monitoring + Observability

- **CloudWatch Logs**: Container stdout/stderr
- **CloudWatch Metrics**: CPU, Memory, Request count
- **CloudWatch Alarms**: Auto-scaling triggers
- **X-Ray**: Distributed tracing (optional)
- **CloudWatch Container Insights**: ECS metrics

---

## Cost Estimate (Monthly)

| Service | Dev/Test | Production |
|---------|----------|------------|
| RDS PostgreSQL | $30 (t3.micro) | $200 (r6g.large Multi-AZ) |
| ElastiCache Redis | $15 (t3.micro) | $150 (r6g.large) |
| ECS Fargate (API) | $30 (0.5 vCPU, 1GB) | $120 (2 vCPU x 2 tasks) |
| ALB | $20 | $20 |
| S3 + CloudFront | $5 | $20 |
| NAT Gateway | $35 | $70 (2 AZ) |
| Secrets Manager | $2 | $5 |
| **Total** | **~$140/mo** | **~$600/mo** |

*Costs vary by region and usage. GPU instances (Ollama) add $400+/mo.*

---

## LLM Service Configuration

### Default: Groq API
Groq provides extremely fast inference (~10x faster than competitors) at competitive pricing.

**Environment Variables:**
```
GROQ_API_KEY=gsk_xxx           # Primary LLM provider
ANTHROPIC_API_KEY=sk-ant-xxx   # Fallback for complex tasks
GOOGLE_API_KEY=xxx             # Alternative provider
OPENAI_API_KEY=sk-xxx          # Alternative provider
```

**Secrets Manager Structure:**
```
postmagiq/llm-keys:
  GROQ_API_KEY: "gsk_xxx"
  ANTHROPIC_API_KEY: "sk-ant-xxx"
  GOOGLE_API_KEY: "xxx"
  OPENAI_API_KEY: "sk-xxx"
```

**No GPU Infrastructure Required** - All LLM calls go to external APIs.
Ollama service can be removed from production deployment.

---

## Implementation Order

### Step 1: Production Dockerfile
Create `Dockerfile.prod` with multi-stage build for smaller images.

### Step 2: Terraform Foundation
Create modules in order:
1. `vpc/` - Network foundation
2. `secrets/` - Store API keys before other services need them
3. `rds/` - Database (longest to provision)
4. `elasticache/` - Redis cache

### Step 3: Compute Layer
1. `ecr/` - Container registry
2. `ecs/` - Cluster and task definitions
3. `alb/` - Load balancer

### Step 4: Frontend + CDN
1. `s3/` - GUI static files + artifacts
2. `cloudfront/` - CDN distribution

### Step 5: CI/CD + Monitoring
1. GitHub Actions workflow
2. `monitoring/` - CloudWatch alarms

### Step 6: Deploy + Validate
1. `terraform apply -var-file=environments/dev.tfvars`
2. Run database migrations
3. Test API endpoints
4. Verify frontend loads
5. Test LLM integrations (Groq default)

---

## Verification Plan

1. **Health Check**: `curl https://api.yourdomain.com/api/health`
2. **Database**: Run migration, verify tables created
3. **Redis**: Check session storage works
4. **LLM**: Run a test workflow with Groq
5. **Frontend**: Access GUI, login, create workspace
6. **Artifacts**: Upload and retrieve workflow artifacts from S3

---

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `Dockerfile.prod` | Production multi-stage build |
| `.github/workflows/deploy.yml` | CI/CD pipeline |
| `docker-compose.prod.yml` | Local prod simulation |

### Terraform Structure (`infra/terraform/`)

```
infra/terraform/
├── main.tf              # Provider config, backend
├── variables.tf         # Input variables
├── outputs.tf           # Output values (URLs, ARNs)
├── environments/
│   ├── dev.tfvars       # Dev environment values
│   └── prod.tfvars      # Prod environment values
├── modules/
│   ├── vpc/             # VPC, subnets, NAT
│   ├── rds/             # PostgreSQL + RDS Proxy
│   ├── elasticache/     # Redis cluster
│   ├── ecs/             # Cluster, services, tasks
│   ├── alb/             # Load balancer, listeners
│   ├── s3/              # Buckets for GUI + artifacts
│   ├── cloudfront/      # CDN distribution
│   ├── secrets/         # Secrets Manager
│   └── monitoring/      # CloudWatch alarms
└── README.md
```

### Environment Configuration

**Dev Environment** (`dev.tfvars`):
```hcl
environment         = "dev"
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a"]  # Single AZ
rds_instance_class = "db.t3.micro"
redis_node_type    = "cache.t3.micro"
ecs_cpu            = 512
ecs_memory         = 1024
ecs_desired_count  = 1
```

**Prod Environment** (`prod.tfvars`):
```hcl
environment         = "prod"
vpc_cidr           = "10.1.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]  # Multi-AZ
rds_instance_class = "db.r6g.large"
rds_multi_az       = true
redis_node_type    = "cache.r6g.large"
ecs_cpu            = 2048
ecs_memory         = 4096
ecs_desired_count  = 2
```

---

## Decisions Made

1. **Infrastructure as Code**: Terraform
2. **LLM Strategy**: External APIs with **Groq as default** (fast inference, cost-effective)
3. **Environment count**: Dev + Prod (2 environments)
4. **Initial Scale**: Minimal (~$140/mo) - single AZ, small instances

---

## Reference Links

- [AWS SaaS Reference Architecture for ECS](https://github.com/aws-samples/saas-reference-architecture-ecs)
- [AWS FastAPI Docker Demo](https://github.com/aws-samples/python-fastapi-demo-docker)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Multi-tenant PostgreSQL RLS](https://github.com/aws-samples/aws-saas-factory-postgresql-rls)
- [Serverless FastAPI with Neon + App Runner](https://neon.com/blog/deploy-a-serverless-fastapi-app-with-neon-postgres-and-aws-app-runner-at-any-scale)
- [ECS Fargate + RDS Best Practices](https://medium.com/@rvisingh1221/ecs-finhacks-scaling-microservices-with-aws-ecs-fargate-and-rds-a7517128ecc3)
