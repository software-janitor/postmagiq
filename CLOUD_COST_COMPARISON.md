# Cloud Cost Comparison: AWS vs GCP

> **Decision: GCP Selected** - See [GCP_DEPLOYMENT_PLAN.md](./GCP_DEPLOYMENT_PLAN.md) for implementation details.

## Overview

This document compares the total cost of deploying Postmagiq on AWS vs GCP, including compute, database, cache, auth, networking, and storage.

**Recommendation: GCP is 46-67% cheaper** for most scenarios due to Cloud Run's scale-to-zero, free auth tier (50k MAU), and no NAT Gateway costs.

---

## Assumptions

| Factor | Value |
|--------|-------|
| Region | US (us-east-1 / us-central1) |
| Traffic | ~100k requests/day (~3M/month) |
| Users | 10,000-100,000 MAU |
| Database | PostgreSQL with 20GB storage |
| Cache | Redis 1GB |
| Storage | 10GB artifacts + 1GB static files |

---

## Minimal Setup (Dev/MVP)

| Component | AWS | GCP | Notes |
|-----------|-----|-----|-------|
| **Compute** | | | |
| API container | $29.50/mo (Fargate 0.5 vCPU, 1GB) | **$0-5/mo** (Cloud Run) | GCP scales to zero |
| **Database** | | | |
| PostgreSQL | $12.50/mo (db.t4g.micro) | **$9.37/mo** (db-f1-micro) | Similar |
| Connection pooling | Included (RDS Proxy free tier) | N/A (not needed) | |
| **Cache** | | | |
| Redis | **$12.40/mo** (cache.t4g.micro) | $32.85/mo (1GB basic) | AWS cheaper |
| **Auth** | | | |
| 10k MAU | **$0** (Cognito free tier) | **$0** (Identity Platform free) | Both free |
| **Networking** | | | |
| Load Balancer | $16.20/mo (ALB) | **$0** (included in Cloud Run) | GCP wins |
| NAT Gateway | $32.40/mo + data | **$0** (Cloud Run direct egress) | GCP wins |
| **Storage** | | | |
| Object storage | $0.25/mo (S3 11GB) | **$0** (5GB free + $0.13) | Similar |
| **CDN** | | | |
| Static hosting | $1/mo (CloudFront) | **$0** (Cloud CDN free tier) | GCP wins |
| **Secrets** | | | |
| Secret Manager | $2/mo (5 secrets) | **$0** (6 versions free) | GCP wins |
| **DNS** | | | |
| Hosted zone | $0.50/mo | $0.20/mo | Similar |
| | | | |
| **TOTAL** | **~$107/mo** | **~$43/mo** | **GCP 60% cheaper** |

---

## Production Setup (HA, Multi-AZ)

| Component | AWS | GCP | Notes |
|-----------|-----|-----|-------|
| **Compute** | | | |
| API (2 instances) | $59/mo (Fargate 0.5 vCPU x2) | $15-30/mo (Cloud Run min instances) | GCP cheaper |
| **Database** | | | |
| PostgreSQL HA | $150/mo (db.t4g.medium Multi-AZ) | $75/mo (db-g1-small HA) | GCP cheaper |
| **Cache** | | | |
| Redis HA | **$50/mo** (cache.t4g.small x2) | $70/mo (Standard tier 1GB) | AWS cheaper |
| **Auth** | | | |
| 50k MAU | $220/mo (Cognito Lite) | **$0** (Identity Platform free) | GCP wins |
| 100k MAU | $495/mo | $275/mo | GCP cheaper |
| **Networking** | | | |
| Load Balancer | $20/mo | $18/mo | Similar |
| NAT Gateway | $65/mo (2 AZ) | **$0** | GCP wins |
| **Storage** | | | |
| Object storage | $2/mo (50GB) | $1/mo | Similar |
| **CDN** | | | |
| CloudFront/CDN | $5/mo | $3/mo | Similar |
| **Monitoring** | | | |
| Logs + Metrics | $15/mo | $10/mo | Similar |
| | | | |
| **TOTAL (50k MAU)** | **~$586/mo** | **~$192/mo** | **GCP 67% cheaper** |
| **TOTAL (100k MAU)** | **~$861/mo** | **~$467/mo** | **GCP 46% cheaper** |

---

## Cost Breakdown by Category

### At 10k MAU (Minimal)

```
AWS ($107/mo)                    GCP ($43/mo)
─────────────────                ─────────────────
Compute:    $29.50  (28%)        Compute:    $5     (12%)
Database:   $12.50  (12%)        Database:   $9.37  (22%)
Cache:      $12.40  (12%)        Cache:      $32.85 (76%) ← GCP weakness
Network:    $48.60  (45%)        Network:    $0     (0%)  ← GCP strength
Other:      $4      (3%)         Other:      $0.20  (0%)
```

### At 50k MAU (Growth)

```
AWS ($586/mo)                    GCP ($192/mo)
─────────────────                ─────────────────
Compute:    $59     (10%)        Compute:    $25    (13%)
Database:   $150    (26%)        Database:   $75    (39%)
Cache:      $50     (9%)         Cache:      $70    (36%)
Auth:       $220    (38%) ←      Auth:       $0     (0%)  ← HUGE difference
Network:    $85     (15%)        Network:    $18    (9%)
Other:      $22     (4%)         Other:      $4     (2%)
```

---

## Scaling Cost Projection

| MAU | AWS Total | GCP Total | Savings with GCP |
|-----|-----------|-----------|------------------|
| 1k | $90 | $40 | 56% |
| 10k | $107 | $43 | 60% |
| 25k | $190 | $65 | 66% |
| 50k | $586 | $192 | 67% |
| 100k | $861 | $467 | 46% |
| 250k | $1,650 | $1,100 | 33% |
| 500k | $2,900 | $2,100 | 28% |

---

## Key Cost Drivers

### Where GCP Wins

| Factor | AWS Cost | GCP Cost | Monthly Savings |
|--------|----------|----------|-----------------|
| Auth (50k MAU) | $220 | $0 | $220 |
| NAT Gateway | $65 | $0 | $65 |
| Compute (idle) | $29+ | $0-5 | $25+ |
| Load Balancer | $20 | $0 (Cloud Run) | $20 |

**Total GCP advantage: ~$330/mo** at 50k MAU

### Where AWS Wins

| Factor | AWS Cost | GCP Cost | Monthly Savings |
|--------|----------|----------|-----------------|
| Redis (1GB) | $12 | $33 | $21 |
| Redis HA | $50 | $70 | $20 |

**Total AWS advantage: ~$20-40/mo** on cache

### Neutral

- Database pricing is similar
- Storage pricing is similar
- CDN pricing is similar
- DNS pricing is similar

---

## Service Mapping

| Component | AWS Service | GCP Service |
|-----------|-------------|-------------|
| Compute | ECS Fargate | Cloud Run |
| Database | RDS PostgreSQL | Cloud SQL PostgreSQL |
| Cache | ElastiCache Redis | Memorystore Redis |
| Auth | Cognito | Identity Platform |
| Storage | S3 | Cloud Storage |
| CDN | CloudFront | Cloud CDN |
| DNS | Route 53 | Cloud DNS |
| Secrets | Secrets Manager | Secret Manager |
| Monitoring | CloudWatch | Cloud Monitoring |
| Load Balancer | ALB | Cloud Load Balancing |
| Container Registry | ECR | Artifact Registry |

---

## Free Tier Comparison

| Service | AWS Free Tier | GCP Free Tier |
|---------|---------------|---------------|
| Compute | 750 hrs/mo (12 months) | 2M requests/mo (forever) |
| Auth | 10,000 MAU | **50,000 MAU** |
| Database | 750 hrs (12 months) | None |
| Storage | 5GB (12 months) | **5GB (forever)** |
| CDN | 1TB/mo (12 months) | Free tier included |
| Secrets | $0.40/secret/mo | **6 versions free** |

---

## Architecture Differences

### AWS (ECS Fargate)

```
Internet → CloudFront → ALB → ECS Fargate (VPC)
                                    ↓
                              NAT Gateway → External APIs
                                    ↓
                              RDS + ElastiCache (private subnet)
```

**Complexity**: High (VPC, subnets, NAT, security groups)

### GCP (Cloud Run)

```
Internet → Cloud Run → External APIs (direct)
               ↓
         Cloud SQL + Memorystore (VPC connector)
```

**Complexity**: Low (no VPC required for Cloud Run)

---

## Recommendations

| Scenario | Recommendation | Reason |
|----------|----------------|--------|
| MVP/Startup | **GCP** | 60% cheaper, simpler architecture |
| < 50k MAU | **GCP** | Free auth, no NAT costs |
| 50k-100k MAU | **GCP** | Still significantly cheaper |
| > 250k MAU | Either | Gap narrows, evaluate features |
| Enterprise compliance | AWS | More certifications, regions |
| Existing AWS shop | AWS | Avoid multi-cloud complexity |

---

## Decision Summary

### Choose GCP If:
- Cost is a primary concern
- You want simpler infrastructure
- You're under 100k MAU
- You prefer pay-per-request compute
- You want generous free auth tier

### Choose AWS If:
- You need specific AWS services
- Enterprise compliance requirements (FedRAMP, HIPAA BAA)
- Your team has AWS expertise
- You need more global regions
- You're already invested in AWS ecosystem

---

## Sources

- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud SQL Pricing](https://cloud.google.com/sql/pricing)
- [GCP Identity Platform Pricing](https://cloud.google.com/identity-platform/pricing)
- [Memorystore Pricing](https://cloud.google.com/memorystore/docs/redis/pricing)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [AWS RDS Pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [AWS Cognito Pricing](https://aws.amazon.com/cognito/pricing/)
- [AWS ElastiCache Pricing](https://aws.amazon.com/elasticache/pricing/)
