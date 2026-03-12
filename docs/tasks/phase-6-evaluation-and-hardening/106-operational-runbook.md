# TASK-106: Operational Runbook Documentation

## Metadata
- **Phase:** 6
- **Module:** infra
- **Priority:** P2-medium
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer / DevOps engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-080, TASK-081, TASK-082, TASK-083, TASK-104]
- **Blocks:** None
- **Related:** None

## Objective
Write an operational runbook documenting deployment procedures, common troubleshooting scenarios, alert response playbooks, catalog update procedures, and monitoring dashboard configuration. This is the on-call engineer's reference for operating Kairos in production.

## Design Reference
- See Design Doc §7 Deployment & Operations (all subsections)

## Technical Requirements

### Inputs / Prerequisites
- All Phase 5 tasks complete (operational features exist to document)
- TASK-104 complete (degradation modes to document)

### Implementation Details

1. **Create `docs/runbook.md`** covering:

   - **Deployment:** How to build, push, and deploy the Docker image. Rolling update strategy. Environment variable reference.
   - **Startup verification:** What to check after deployment (health, readiness, metrics, version endpoint).
   - **Catalog updates:** Step-by-step for updating catalog.json and embeddings.json (extract → enrich → review → embed → validate → deploy or hot-reload).
   - **Threshold tuning:** How to run the eval harness, tune thresholds, and apply changes.
   - **Troubleshooting:**
     - High null response rate → check catalog coverage, run eval, review top_candidates
     - High latency → check Azure AI metrics, check Tier 3 invocation rate
     - Degraded mode active → check Azure AI Foundry status, verify credentials
     - Rate limiting errors → check client request patterns, adjust limits
   - **Monitoring:** Key metrics to watch, alert thresholds, Grafana dashboard configuration.
   - **Incident response:** Escalation paths for service degradation.

### Tech Stack & Dependencies
- None — documentation only

## Acceptance Criteria
1. Runbook covers all deployment procedures
2. Runbook includes at least 5 troubleshooting scenarios with step-by-step resolution
3. Runbook documents all admin endpoints and their usage
4. Runbook includes monitoring alert threshold recommendations
5. Runbook is reviewed by at least one other team member

## Testing Requirements
- **Unit Tests:** None
- **Integration Tests:** None
- **Manual Verification:** Walk through each runbook procedure to verify accuracy.

## Files to Create/Modify
- `docs/runbook.md` — (create) Operational runbook

## Risks & Edge Cases
- Documentation drift: the runbook must be updated whenever operational procedures change. Include a "last updated" timestamp.

## Notes
- The runbook is a living document. Start with the essentials and iterate.
