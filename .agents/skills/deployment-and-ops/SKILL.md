---
name: deployment-and-ops
description: "⚠️ MANDATORY: Core guidelines for server operations, local zero-alert deployment scripts, and verifying service health."
---

# Deployment and Operations

This document defines standard operating procedures for deployment, server operations, cache warmups, and live verification of the X-Analytics service.

---

## 1. Deployment Architecture & Security Policy

### 1.1 Native Host Build & Deployment Pipeline
1. **Application Code (`x-analytics`)**:
   - Focuses strictly on business logic, automated tests, and Dockerfile definitions. Contains zero server infrastructure configs or connection credentials.
   - GitHub Actions (`docker-publish.yml`) is retained purely as a manual emergency fallback (`workflow_dispatch`), avoiding unnecessary CI compute runs.
2. **Unified Deployment (`x-actions/deploy.sh`)**:
   - Production deployment is executed exclusively from the private repository `/Users/xera/GitHub/x-actions` via `./deploy.sh`.
   - The deployment script syncs source code incrementally via rsync over trusted domestic SSH connections, performs native high-speed Docker builds directly on target host architectures (`a1` linux/arm64, `aliyun` linux/amd64), recreates containers, and conducts automated health checks (`/api/health`).
   - *Zero Foreign SSH*: Eliminates overseas cloud login alerts from foreign GitHub Actions runners.

---

## 2. Deploying Applications & Infrastructure

All production deployments are centrally managed in `x-actions`:

```bash
cd /Users/xera/GitHub/x-actions

# Deploy to primary server (a1)
./deploy.sh

# Deploy to specific target or all targets
./deploy.sh --target aliyun
./deploy.sh --target all

# View status or logs
./deploy.sh --status
./deploy.sh --logs
```

---

## 3. Deploying `x-actions` (Gateway & Infrastructure)

When modifying `nginx.conf` or `docker-compose.yml` in the `x-actions` repository:

```bash
cd /Users/xera/GitHub/x-actions

# Full config sync & container rollout
./deploy.sh

# Hot-reload Nginx configuration only (zero downtime, ~1s)
./deploy.sh --infra-only

# Check container status across all production servers
./deploy.sh --status --target all
```

---

## 4. Live Verification & Cache Operations

### 4.1 Verifying Live Deployment
To verify that the production service is responding:
```bash
# Verify gateway response over unified HTTPS subpath
curl -sI https://xera.dpdns.org/analytics/

# Check specific script version or HTML assets
curl -s https://xera.dpdns.org/analytics/ | grep main.js

# Check internal direct port health (on server host or via SSH)
curl -s http://127.0.0.1:2012/api/health
```

### 4.2 Cache Control APIs
- **Manual Cache Warmup**: `POST https://xera.dpdns.org/analytics/api/cache/warmup` (requires `X-Admin-Token` header)
- **Clear All Caches**: `DELETE https://xera.dpdns.org/analytics/api/cache/clear` (requires `X-Admin-Token` header)
- **Clear Specific Pattern**: `DELETE https://xera.dpdns.org/analytics/api/cache/clear/{pattern}` (requires `X-Admin-Token` header)
  - Example: `DELETE https://xera.dpdns.org/analytics/api/cache/clear/qdii:passive_funds*`

---

## ⚙️ Language Policy

> **All content in `.agents/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
