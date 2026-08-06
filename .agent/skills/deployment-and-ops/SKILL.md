---
name: deployment-and-ops
description: "⚠️ MANDATORY: Core guidelines for server operations, triggering CI/CD deploy jobs, and verifying service health."
---

# Deployment and Operations

This document defines standard operating procedures for deployment, cache warmups, and server-side verification of the X-Analytics service.

---

## 1. Automated CI/CD Pipeline

The project uses a two-repo automated CI/CD pipeline:
1. **Build & Push (`x-analytics`)**:
   - Pushing code to `main` branch triggers GitHub Actions to build the Docker image and push it to the Aliyun Container Registry (`crpi-8pt82bfwac9xhe36.cn-shenzhen.personal.cr.aliyuncs.com/xera_2011/x-analytics:latest`).
2. **Pull & Deploy (`x-actions`)**:
   - Pushing config changes or triggering manually triggers GitHub Actions in the `x-actions` repository to SSH into the Aliyun VPS, pull the latest image, and restart the container (`docker compose up -d`).

---

## 2. Triggering Deployments from Local CLI

Do **NOT** make dummy commits or comments to `x-actions` to trigger a deployment. Instead, use the GitHub CLI (`gh`) tool directly from the terminal.

### 2.1 Pre-requisites
Ensure the `gh` tool is logged in and has `workflow` scopes:
```bash
gh auth status
```

### 2.2 Triggering the Deploy Workflow
To trigger the deployment workflow in the `x-actions` repository:
```bash
gh workflow run deploy-aliyun.yml --repo XERA-2011/x-actions
```

> [!IMPORTANT]
> **Race Condition Warning**: Always wait for the `Build and Push` workflow in `x-analytics` to finish (`Status: completed, Conclusion: success`) before triggering the deploy workflow in `x-actions`. Otherwise, the server will pull the old image.

### 2.3 Monitoring Deploy Progress
To check the execution status of the triggered workflow:
```bash
gh run list --workflow=deploy-aliyun.yml --repo XERA-2011/x-actions --limit 3
# Or watch it interactively:
gh run watch --repo XERA-2011/x-actions
```

---

## 3. Server Verification & Operations

### 3.1 Verifying Live Deployment
To verify if new code or script changes are successfully serving on the production site, curl the base path and search for the script version parameters (cache bumps):
```bash
curl -s http://<vps-ip>/analytics/ | grep qdii.js
```

### 3.2 Cache Control APIs
- **Manual Cache Warmup**: `POST /api/cache/warmup`
- **Clear All Caches**: `DELETE /api/cache/clear`
- **Clear Matching Cache Pattern**: `DELETE /api/cache/clear/{pattern}`
  - Example: `DELETE /api/cache/clear/qdii:top_holdings_v5*`

---
