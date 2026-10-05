---
name: deployment-and-ops
description: "⚠️ MANDATORY: Core guidelines for server operations, local zero-alert deployment scripts, and verifying service health."
---

# Deployment and Operations

This document defines standard operating procedures for deployment, server operations, cache warmups, and live verification of the X-Analytics service.

---

## 1. Deployment Architecture & Security Policy

### 1.1 Two-Stage Pipeline
1. **Image Build (`x-analytics`)**:
   - Pushing code to `main` branch triggers GitHub Actions (`docker-publish.yml`) to build multi-arch Docker images (`linux/amd64,linux/arm64`) and push to GHCR and Aliyun Container Registry.
   - *Security Note*: The build runs entirely on GitHub compute and pushes via Registry HTTPS APIs. It never connects directly to servers and contains zero server credentials.
2. **Unified Deployment (`x-actions/deploy.sh`)**:
   - Production deployment is executed exclusively from the private repository `/Users/xera/GitHub/x-actions` via `./deploy.sh`.
   - The deployment script connects directly to target servers (`a1`, `aliyun`, or `--target all`) via trusted domestic SSH connections configured in `~/.ssh/config`.

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

# Full config sync & Nginx restart (~5s)
./deploy.sh

# Hot-reload Nginx only (zero downtime, ~1s)
./deploy.sh --nginx-only

# Test Nginx syntax on production server
./deploy.sh --test
```

---

## 4. Live Verification & Cache Operations

### 4.1 Verifying Live Deployment
To verify that the production service is responding:
```bash
# Verify base page response
curl -sI http://<server-ip>:2012/?tab=qdii

# Check specific script version or module asset
curl -s http://<server-ip>:2012/?tab=qdii | grep qdii.js
```

### 4.2 Cache Control APIs
- **Manual Cache Warmup**: `POST http://<server-ip>:2012/api/cache/warmup` (requires `X-Admin-Token` header)
- **Clear All Caches**: `DELETE http://<server-ip>:2012/api/cache/clear` (requires `X-Admin-Token` header)
- **Clear Specific Pattern**: `DELETE http://<server-ip>:2012/api/cache/clear/{pattern}` (requires `X-Admin-Token` header)
  - Example: `DELETE http://<server-ip>:2012/api/cache/clear/qdii:passive_funds*`

---

## ⚙️ Language Policy

> **All content in `.agents/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
