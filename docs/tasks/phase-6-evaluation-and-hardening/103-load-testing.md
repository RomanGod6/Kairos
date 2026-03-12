# TASK-103: Load Testing

## Metadata
- **Phase:** 6
- **Module:** infra
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer / DevOps engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-060, TASK-080, TASK-081]
- **Blocks:** None
- **Related:** [TASK-062]

## Objective
Create load test scripts using `hey` or `k6` that validate the service meets its performance targets: p95 latency under 500ms at 100 concurrent requests, sustained 500 req/min throughput, and no errors under load.

## Design Reference
- See Design Doc §10 Performance Targets
- See Design Doc §10.1 Latency SLOs

## Technical Requirements

### Inputs / Prerequisites
- TASK-060 complete (classify endpoint)
- TASK-080 complete (Docker image for consistent test environment)
- TASK-081 complete (metrics for monitoring during tests)

### Implementation Details

1. **Create `scripts/loadtest/loadtest.sh`:**

   ```bash
   #!/bin/bash
   # Load test for Kairos classification endpoint
   # Requires: hey (go install github.com/rakyll/hey@latest)

   BASE_URL="${KAIROS_URL:-http://localhost:8080}"
   API_KEY="${KAIROS_API_KEY:-changeme}"

   echo "=== Kairos Load Test ==="
   echo "Target: $BASE_URL"

   # Test 1: Sustained throughput (500 req/min for 2 minutes)
   echo "--- Test 1: Sustained throughput ---"
   hey -n 1000 -c 10 -m POST \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"message":"my endpoints are not checking in"}' \
     "$BASE_URL/v1/classify"

   # Test 2: Burst concurrency (100 concurrent)
   echo "--- Test 2: Burst concurrency ---"
   hey -n 500 -c 100 -m POST \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"message":"backup failed for client server"}' \
     "$BASE_URL/v1/classify"

   # Test 3: Keyword (Tier 1) latency baseline
   echo "--- Test 3: Tier 1 latency ---"
   hey -n 1000 -c 50 -m POST \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"message":"VSA"}' \
     "$BASE_URL/v1/classify"
   ```

2. **Add Makefile target:**
   ```makefile
   loadtest:
   	bash scripts/loadtest/loadtest.sh
   ```

3. **Define pass/fail criteria:**
   - p95 latency < 500ms for Tier 1 + Tier 2 queries
   - p99 latency < 2000ms (includes Tier 3 reranker)
   - 0% error rate at sustained 500 req/min
   - No memory leaks (RSS stays flat over 5-minute test)

### Tech Stack & Dependencies
- `hey` — HTTP load generator (`go install github.com/rakyll/hey@latest`)
- Alternative: `k6` for more complex scripting

## Acceptance Criteria
1. Load test script runs against local or remote Kairos instance
2. Sustained throughput test confirms 500 req/min capacity
3. Burst concurrency test confirms 100 concurrent connections handled
4. p95 latency is under 500ms for Tier 1/Tier 2 queries
5. Zero error rate under normal load
6. Results are printed in a readable format with latency percentiles

## Testing Requirements
- **Unit Tests:** None — this is an external testing tool
- **Integration Tests:** Run against dockerized Kairos service
- **Manual Verification:** Run `make loadtest`, review output

## Files to Create/Modify
- `scripts/loadtest/loadtest.sh` — (create) Load test script
- `Makefile` — (modify) Add `loadtest` target

## Risks & Edge Cases
- Load tests against shared environments could impact other services. Always run against isolated instances.
- Azure AI Foundry rate limits may cause failures under load test. Use offline mode or mock Azure responses for pure load testing.

## Notes
- Run load tests before every release to catch performance regressions.
