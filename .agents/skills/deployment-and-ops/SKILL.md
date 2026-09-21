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
   - Pushing code to `main` branch triggers GitHub Actions (`docker-publish.yml`) to build the Docker image and push it to Aliyun Container Registry (`crpi-8pt82bfwac9xhe36.cn-shenzhen.personal.cr.aliyuncs.com/xera_2011/x-analytics:latest`).
   - *Security Note*: The build runs entirely on GitHub compute and pushes via Aliyun ACR HTTPS API. It **never** connects to the ECS server and will **never** trigger security alerts.
2. **Local Direct Deploy (`deploy.sh`)**:
   - Deployment to the production ECS server (`8.129.84.229`) is executed directly from the local developer machine via domestic SSH.

### 1.2 ⚠️ Zero Foreign SSH Login Rule
> [!IMPORTANT]
> **NEVER trigger remote SSH actions from GitHub Actions (`deploy-aliyun.yml`) or overseas runner IPs.**
> GitHub Actions runners operate in Microsoft Azure foreign data centers (US/Europe). Logging into ECS `root` from foreign IPs triggers Aliyun Cloud Shield high-severity security email alerts (`【ECS在非常用地登录】服务器异常登录提醒`).
> All production SSH triggers MUST originate from the local machine's trusted domestic IP via `./deploy.sh`.

---

## 2. Deploying `x-analytics` (Application Code)

The root directory contains an automated deployment script: [`./deploy.sh`](file:///Users/xera/GitHub/x-analytics/deploy.sh).

### 2.1 Standard One-Click Release
Run without arguments to execute the full end-to-end pipeline:
```bash
./deploy.sh
```
This automated workflow:
1. Checks for uncommitted changes (prompts to commit if dirty).
2. Pushes commits to `origin main`.
3. Discovers and tracks the GitHub Actions build run (`gh run watch`).
4. Once the ACR image is ready, establishes local SSH to `root@8.129.84.229`:
   - `docker compose pull xanalytics`
   - `docker compose up -d --force-recreate --remove-orphans xanalytics`
   - `docker image prune -f`
5. Performs multi-round health check (`HTTP 200` verification) and reports duration.

### 2.2 Fast Deploy (Image Already Built)
If the Docker image is already built on ACR (or re-deploying after an earlier build):
```bash
./deploy.sh --skip-build   # or -s (completes in ~10 seconds)
```

### 2.3 Container Management & Troubleshooting
```bash
# View live application logs (streaming tail)
./deploy.sh --logs         # or -l

# Restart xanalytics container without pulling image
./deploy.sh --restart      # or -r

# Inspect status of all containers on production server
./deploy.sh --status
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
curl -sI http://8.129.84.229:2012/?tab=qdii

# Check specific script version or module asset
curl -s http://8.129.84.229:2012/?tab=qdii | grep qdii.js
```

### 4.2 Cache Control APIs
- **Manual Cache Warmup**: `POST http://8.129.84.229:2012/api/cache/warmup`
- **Clear All Caches**: `DELETE http://8.129.84.229:2012/api/cache/clear`
- **Clear Specific Pattern**: `DELETE http://8.129.84.229:2012/api/cache/clear/{pattern}`
  - Example: `DELETE http://8.129.84.229:2012/api/cache/clear/qdii:passive_funds*`

---

## ⚙️ Language Policy

> **All content in `.agents/` directory MUST be written in English.**
> This ensures consistency and optimal AI comprehension.
