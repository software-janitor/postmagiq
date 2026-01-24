# GCP Deployment Plan for Postmagiq

## Architecture Overview

```
                              ┌─────────────────┐
                              │   Cloud DNS     │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Cloud Load     │
                              │  Balancing      │
                              └────────┬────────┘
                                       │
               ┌───────────────────────┼───────────────────────┐
               │                       │                       │
      ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
      │  Cloud Storage  │    │   Cloud Run     │    │  Cloud Storage  │
      │  (GUI Static)   │    │   (API)         │    │  (Artifacts)    │
      └─────────────────┘    └────────┬────────┘    └─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
           ┌────────▼───────┐  ┌──────▼──────┐  ┌──────▼──────┐
           │  Cloud SQL     │  │ Memorystore │  │  Secret     │
           │  PostgreSQL    │  │ Redis       │  │  Manager    │
           └────────────────┘  └─────────────┘  └─────────────┘
```

---

## GCP Services Mapping

| Component | GCP Service | Pricing |
|-----------|-------------|---------|
| API (FastAPI) | Cloud Run | $0 (2M req/mo free) |
| Database | Cloud SQL PostgreSQL | ~$9/mo (db-f1-micro) |
| Cache | Memorystore Redis | ~$33/mo (1GB basic) |
| Static Frontend | Cloud Storage + CDN | ~$0 (5GB free) |
| Artifacts | Cloud Storage | ~$0 (5GB free) |
| Auth | Identity Platform | $0 (50k MAU free) |
| Secrets | Secret Manager | $0 (6 versions free) |
| DNS | Cloud DNS | $0.20/zone/mo |
| Logging | Cloud Logging | $0 (50GB free) |
| Monitoring | Cloud Monitoring | $0 (basic free) |

**Estimated Total: ~$43/mo** (minimal setup)

---

## Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| IaC | Terraform | Industry standard, GCP provider mature |
| LLM | Groq (default) + Anthropic/Google fallback | Fast, cost-effective |
| Auth | Keep custom + GCP Identity Platform | 50k MAU free |
| Environments | Dev + Prod | Start simple |
| Region | us-central1 | Free tier eligible, low latency |
| Logging | Exclusion filters + Storage archive | Stay under 50GB free |

---

## Phase 1: Project Setup

### 1.1 Create GCP Project
```bash
# Create project
gcloud projects create postmagiq-prod --name="Postmagiq Production"
gcloud projects create postmagiq-dev --name="Postmagiq Dev"

# Set default project
gcloud config set project postmagiq-prod

# Enable billing
gcloud billing accounts list
gcloud billing projects link postmagiq-prod --billing-account=XXXXXX-XXXXXX-XXXXXX
```

### 1.2 Enable Required APIs
```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudresourcemanager.googleapis.com \
  identitytoolkit.googleapis.com \
  compute.googleapis.com \
  dns.googleapis.com
```

### 1.3 Create Service Account
```bash
# Create service account for Cloud Run
gcloud iam service-accounts create postmagiq-api \
  --display-name="Postmagiq API Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding postmagiq-prod \
  --member="serviceAccount:postmagiq-api@postmagiq-prod.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding postmagiq-prod \
  --member="serviceAccount:postmagiq-api@postmagiq-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding postmagiq-prod \
  --member="serviceAccount:postmagiq-api@postmagiq-prod.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## Phase 2: Database (Cloud SQL)

### 2.1 Create PostgreSQL Instance
```bash
# Dev instance (smallest, ~$9/mo)
gcloud sql instances create postmagiq-db-dev \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB \
  --storage-type=SSD \
  --backup-start-time=03:00 \
  --availability-type=zonal

# Prod instance (HA, ~$75/mo)
gcloud sql instances create postmagiq-db-prod \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --region=us-central1 \
  --storage-size=20GB \
  --storage-type=SSD \
  --backup-start-time=03:00 \
  --availability-type=regional  # HA
```

### 2.2 Create Database and User
```bash
# Set password
gcloud sql users set-password postgres \
  --instance=postmagiq-db-dev \
  --password=SECURE_PASSWORD_HERE

# Create database
gcloud sql databases create orchestrator \
  --instance=postmagiq-db-dev

# Enable pgvector extension (via Cloud SQL Studio or psql)
# CREATE EXTENSION IF NOT EXISTS vector;
```

### 2.3 Connection String
```
# For Cloud Run (via Unix socket)
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@/orchestrator?host=/cloudsql/PROJECT:REGION:INSTANCE

# Example
DATABASE_URL=postgresql+asyncpg://postgres:xxx@/orchestrator?host=/cloudsql/postmagiq-prod:us-central1:postmagiq-db-prod
```

---

## Phase 3: Cache (Memorystore Redis)

### 3.1 Create VPC Connector (Required for Memorystore)
```bash
# Create VPC connector for Cloud Run to access Memorystore
gcloud compute networks vpc-access connectors create postmagiq-connector \
  --region=us-central1 \
  --range=10.8.0.0/28
```

### 3.2 Create Redis Instance
```bash
# Dev/Prod instance (~$33/mo for 1GB basic)
gcloud redis instances create postmagiq-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=basic

# Get connection info
gcloud redis instances describe postmagiq-redis --region=us-central1
```

### 3.3 Connection String
```
REDIS_URL=redis://10.x.x.x:6379  # Internal IP from describe command
```

---

## Phase 4: Secrets Manager

### 4.1 Create Secrets
```bash
# Database password
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create db-password --data-file=-

# JWT secret
openssl rand -base64 32 | gcloud secrets create jwt-secret --data-file=-

# LLM API keys
echo -n "gsk_xxx" | gcloud secrets create groq-api-key --data-file=-
echo -n "sk-ant-xxx" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "xxx" | gcloud secrets create google-api-key --data-file=-

# Stripe (if using)
echo -n "sk_xxx" | gcloud secrets create stripe-secret-key --data-file=-
echo -n "whsec_xxx" | gcloud secrets create stripe-webhook-secret --data-file=-
```

### 4.2 Grant Access to Cloud Run
```bash
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:postmagiq-api@postmagiq-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for other secrets...
```

---

## Phase 5: Container Registry

### 5.1 Create Artifact Registry
```bash
gcloud artifacts repositories create postmagiq \
  --repository-format=docker \
  --location=us-central1 \
  --description="Postmagiq container images"
```

### 5.2 Build and Push Image
```bash
# Configure Docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build image
docker build -t us-central1-docker.pkg.dev/postmagiq-prod/postmagiq/api:latest -f Dockerfile.prod .

# Push image
docker push us-central1-docker.pkg.dev/postmagiq-prod/postmagiq/api:latest
```

---

## Phase 6: Cloud Run Deployment

### 6.1 Deploy API Service
```bash
gcloud run deploy postmagiq-api \
  --image=us-central1-docker.pkg.dev/postmagiq-prod/postmagiq/api:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --service-account=postmagiq-api@postmagiq-prod.iam.gserviceaccount.com \
  --vpc-connector=postmagiq-connector \
  --add-cloudsql-instances=postmagiq-prod:us-central1:postmagiq-db-prod \
  --set-secrets=DATABASE_PASSWORD=db-password:latest,JWT_SECRET=jwt-secret:latest,GROQ_API_KEY=groq-api-key:latest \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:\${DATABASE_PASSWORD}@/orchestrator?host=/cloudsql/postmagiq-prod:us-central1:postmagiq-db-prod" \
  --set-env-vars="REDIS_URL=redis://10.x.x.x:6379" \
  --min-instances=0 \
  --max-instances=10 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=300 \
  --concurrency=80
```

### 6.2 Cloud Run Service YAML (Alternative)
```yaml
# cloud-run-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: postmagiq-api
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cloudsql-instances: postmagiq-prod:us-central1:postmagiq-db-prod
        run.googleapis.com/vpc-access-connector: postmagiq-connector
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      serviceAccountName: postmagiq-api@postmagiq-prod.iam.gserviceaccount.com
      containers:
        - image: us-central1-docker.pkg.dev/postmagiq-prod/postmagiq/api:latest
          ports:
            - containerPort: 8000
          resources:
            limits:
              cpu: "1"
              memory: 512Mi
          env:
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-password
                  key: latest
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: jwt-secret
                  key: latest
```

---

## Phase 7: Static Frontend (Cloud Storage + CDN)

### 7.1 Create Bucket
```bash
# Create bucket for static files
gsutil mb -l us-central1 gs://postmagiq-gui-prod

# Enable website hosting
gsutil web set -m index.html -e index.html gs://postmagiq-gui-prod

# Make public
gsutil iam ch allUsers:objectViewer gs://postmagiq-gui-prod
```

### 7.2 Build and Deploy Frontend
```bash
cd gui
npm run build
gsutil -m rsync -r -d dist/ gs://postmagiq-gui-prod/
```

### 7.3 Set Up Cloud CDN (Optional)
```bash
# Create backend bucket
gcloud compute backend-buckets create postmagiq-gui-backend \
  --gcs-bucket-name=postmagiq-gui-prod \
  --enable-cdn

# Create URL map
gcloud compute url-maps create postmagiq-lb \
  --default-backend-bucket=postmagiq-gui-backend

# Create HTTPS proxy (requires SSL cert)
gcloud compute target-https-proxies create postmagiq-https-proxy \
  --url-map=postmagiq-lb \
  --ssl-certificates=postmagiq-cert

# Create forwarding rule
gcloud compute forwarding-rules create postmagiq-https-rule \
  --global \
  --target-https-proxy=postmagiq-https-proxy \
  --ports=443
```

---

## Phase 8: Storage for Artifacts

### 8.1 Create Artifacts Bucket
```bash
# Create bucket for workflow artifacts
gsutil mb -l us-central1 gs://postmagiq-artifacts-prod

# Set lifecycle policy (archive after 30 days, delete after 1 year)
gsutil lifecycle set lifecycle.json gs://postmagiq-artifacts-prod
```

### 8.2 Lifecycle Policy
```json
{
  "rule": [
    {
      "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
      "condition": {"age": 30}
    },
    {
      "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
      "condition": {"age": 90}
    },
    {
      "action": {"type": "Delete"},
      "condition": {"age": 365}
    }
  ]
}
```

---

## Phase 9: Logging Optimization

### 9.1 Create Log Exclusions
```bash
# Exclude health check logs
gcloud logging sinks update _Default \
  --add-exclusion='name=health-checks,filter=httpRequest.requestUrl=~"/api/health"'

# Exclude debug logs
gcloud logging sinks update _Default \
  --add-exclusion='name=debug-logs,filter=severity="DEBUG"'
```

### 9.2 Archive Old Logs to Storage
```bash
# Create log archive bucket
gsutil mb -l us-central1 gs://postmagiq-logs-archive

# Create log sink for archiving
gcloud logging sinks create logs-archive \
  storage.googleapis.com/postmagiq-logs-archive \
  --log-filter='resource.type="cloud_run_revision" AND severity < "WARNING"'
```

---

## Phase 10: CI/CD Pipeline

### 10.1 Cloud Build Trigger
```yaml
# cloudbuild.yaml
steps:
  # Build API image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/postmagiq/api:$COMMIT_SHA', '-f', 'Dockerfile.prod', '.']

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/postmagiq/api:$COMMIT_SHA']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'postmagiq-api'
      - '--image=us-central1-docker.pkg.dev/$PROJECT_ID/postmagiq/api:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'

  # Build and deploy frontend
  - name: 'node:20'
    dir: 'gui'
    entrypoint: npm
    args: ['ci']

  - name: 'node:20'
    dir: 'gui'
    entrypoint: npm
    args: ['run', 'build']

  - name: 'gcr.io/cloud-builders/gsutil'
    args: ['-m', 'rsync', '-r', '-d', 'gui/dist/', 'gs://postmagiq-gui-prod/']

images:
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/postmagiq/api:$COMMIT_SHA'

options:
  logging: CLOUD_LOGGING_ONLY
```

### 10.2 Create Trigger
```bash
gcloud builds triggers create github \
  --repo-name=postmagiq \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## Phase 11: DNS & SSL

### 11.1 Create DNS Zone
```bash
gcloud dns managed-zones create postmagiq-zone \
  --dns-name="yourdomain.com." \
  --description="Postmagiq DNS zone"
```

### 11.2 Create SSL Certificate
```bash
# Managed SSL certificate (auto-renews)
gcloud compute ssl-certificates create postmagiq-cert \
  --domains=api.yourdomain.com,app.yourdomain.com \
  --global
```

### 11.3 Map Custom Domain to Cloud Run
```bash
gcloud run domain-mappings create \
  --service=postmagiq-api \
  --domain=api.yourdomain.com \
  --region=us-central1
```

---

## Terraform Structure

```
infra/terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── environments/
│   ├── dev.tfvars
│   └── prod.tfvars
└── modules/
    ├── cloud-run/
    ├── cloud-sql/
    ├── memorystore/
    ├── storage/
    ├── secrets/
    └── networking/
```

### main.tf (Example)
```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "postmagiq-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "cloud_sql" {
  source        = "./modules/cloud-sql"
  instance_name = "postmagiq-db-${var.environment}"
  tier          = var.db_tier
  region        = var.region
}

module "memorystore" {
  source        = "./modules/memorystore"
  instance_name = "postmagiq-redis-${var.environment}"
  memory_size   = var.redis_memory_size
  region        = var.region
}

module "cloud_run" {
  source              = "./modules/cloud-run"
  service_name        = "postmagiq-api"
  image               = var.api_image
  region              = var.region
  cloudsql_connection = module.cloud_sql.connection_name
  vpc_connector       = module.networking.vpc_connector_id

  depends_on = [module.cloud_sql, module.memorystore]
}
```

### dev.tfvars
```hcl
project_id       = "postmagiq-dev"
environment      = "dev"
region           = "us-central1"
db_tier          = "db-f1-micro"
redis_memory_size = 1
api_image        = "us-central1-docker.pkg.dev/postmagiq-dev/postmagiq/api:latest"
```

### prod.tfvars
```hcl
project_id       = "postmagiq-prod"
environment      = "prod"
region           = "us-central1"
db_tier          = "db-g1-small"
redis_memory_size = 1
api_image        = "us-central1-docker.pkg.dev/postmagiq-prod/postmagiq/api:latest"
```

---

## Production Dockerfile

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY api/ ./api/
COPY runner/ ./runner/
COPY prompts/ ./prompts/
COPY workflow_config.yaml .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run with uvicorn
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Verification Checklist

1. [ ] GCP project created and billing enabled
2. [ ] APIs enabled (Cloud Run, Cloud SQL, etc.)
3. [ ] Service account created with proper roles
4. [ ] Cloud SQL PostgreSQL running with pgvector
5. [ ] Memorystore Redis running
6. [ ] Secrets stored in Secret Manager
7. [ ] Container image built and pushed to Artifact Registry
8. [ ] Cloud Run service deployed and healthy
9. [ ] VPC connector created for Redis access
10. [ ] Static frontend deployed to Cloud Storage
11. [ ] DNS configured and SSL certificate active
12. [ ] CI/CD pipeline working
13. [ ] Log exclusions configured
14. [ ] Database migrations run successfully
15. [ ] End-to-end test passing

---

## Cost Summary

| Service | Dev | Prod |
|---------|-----|------|
| Cloud Run | $0-5 | $15-30 |
| Cloud SQL | $9 | $75 |
| Memorystore | $33 | $70 |
| Cloud Storage | $0 | $1 |
| Secret Manager | $0 | $0 |
| Cloud DNS | $0.20 | $0.20 |
| Identity Platform | $0 | $0 |
| Logging | $0 | $0-5 |
| **Total** | **~$43/mo** | **~$165/mo** |

---

## Next Steps

1. Create `Dockerfile.prod` in project root
2. Set up Terraform structure in `infra/terraform/`
3. Create GCP projects (dev + prod)
4. Deploy infrastructure with Terraform
5. Run database migrations
6. Deploy API and frontend
7. Configure custom domain
8. Set up CI/CD pipeline

---

## Useful Commands

```bash
# View Cloud Run logs
gcloud run services logs read postmagiq-api --region=us-central1

# Connect to Cloud SQL
gcloud sql connect postmagiq-db-prod --user=postgres

# Update Cloud Run service
gcloud run services update postmagiq-api --region=us-central1 --update-env-vars=KEY=value

# View secrets
gcloud secrets versions access latest --secret=jwt-secret

# Check Redis connection
gcloud redis instances describe postmagiq-redis --region=us-central1
```
