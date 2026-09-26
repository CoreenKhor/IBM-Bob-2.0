# Release Readiness Dossier & Deployment Plan

## 1. Release Overview

| Parameter | Details |
| :--- | :--- |
| **Target Release Version** | `v2.4.0` |
| **Commit Range** | `v2.3.2...main` (`<count>` commits) |
| **Readiness Status** | `GO / NO-GO: GO WITH STAGING VERIFICATION` |
| **Database Migrations** | 1 non-destructive migration |
| **New Env Variables** | 1 new variable (`STRIPE_WEBHOOK_SECRET`) |

---

## 2. Risk Assessment Summary

- **High-Risk Items**: None.
- **Medium-Risk Items**: Database migration adds new nullable column `retry_count` to `orders` table. Backward compatible with current v2.3.2 instances.
- **Rollback Feasibility**: Low risk. Zero destructive operations.

---

## 3. Deployment Checklist

- [ ] **Pre-Deployment**: Apply database migration `0024_add_retry_count.sql`.
- [ ] **Environment Configuration**: Set `STRIPE_WEBHOOK_SECRET` in Kubernetes secrets store.
- [ ] **Canary Rollout**: Deploy to 10% traffic in US-East region; monitor error rates for 15 minutes.
- [ ] **Full Production Deploy**: Promote to 100% traffic across all regions.
- [ ] **Post-Deploy Smoke Test**: Execute synthetic checkout test.

---

## 4. Release Notes (Changelog)

### 🚀 New Features
- **Payment Retries**: Added automated exponential backoff for failed checkout webhooks (#482).
- **Dashboard Search**: Fast full-text indexing for customer accounts (#491).

### 🐛 Bug Fixes
- **Session Expiry**: Resolved race condition causing false-positive logouts during token refresh (#479).
- **Timezone Parsing**: Corrected UTC offset calculation in scheduled report exports (#488).

### ⚙️ Maintenance & Dependency Updates
- Upgraded `typescript` from 5.2.2 to 5.4.5.
- Upgraded `axios` to 1.7.2 to patch security advisory CVE-2024-XXXXX.
