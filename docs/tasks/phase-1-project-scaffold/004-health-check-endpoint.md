# TASK-004: Health Check and Readiness Endpoints

## Metadata
- **Phase:** 1
- **Module:** api
- **Priority:** P0-critical
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003]
- **Blocks:** [TASK-080]
- **Related:** [TASK-022]

## Objective
Implement `/healthz` (liveness) and `/readyz` (readiness) endpoints that Kubernetes and load balancers use to determine if the service is alive and ready to accept traffic. The readiness check verifies that the product catalog is loaded.

## Design Reference
- See Design Doc §7 Deployment & Operations (health checks)
- See Design Doc §5 API Contract (non-authenticated endpoints)

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (HTTP server with chi router)

### Implementation Details

1. **Implement health check handlers in `internal/api/handler.go`:**

   ```go
   package api

   import (
       "encoding/json"
       "net/http"
       "sync/atomic"
   )

   // ReadinessState tracks whether the service is ready to accept traffic.
   type ReadinessState struct {
       ready atomic.Bool
   }

   // NewReadinessState creates a new readiness tracker, initially not ready.
   func NewReadinessState() *ReadinessState {
       return &ReadinessState{}
   }

   // SetReady marks the service as ready.
   func (rs *ReadinessState) SetReady(ready bool) {
       rs.ready.Store(ready)
   }

   // IsReady returns the current readiness state.
   func (rs *ReadinessState) IsReady() bool {
       return rs.ready.Load()
   }

   // HealthResponse is the JSON response for health check endpoints.
   type HealthResponse struct {
       Status string `json:"status"`
   }

   // ReadinessResponse extends HealthResponse with detail about what is/isn't ready.
   type ReadinessResponse struct {
       Status  string            `json:"status"`
       Checks  map[string]string `json:"checks"`
   }

   // HealthCheckHandler returns a simple liveness probe handler.
   // It always returns 200 if the process is running.
   func HealthCheckHandler() http.HandlerFunc {
       return func(w http.ResponseWriter, r *http.Request) {
           w.Header().Set("Content-Type", "application/json")
           w.WriteHeader(http.StatusOK)
           json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
       }
   }

   // ReadinessCheckHandler returns a readiness probe handler.
   // It returns 200 only when the catalog is loaded and the service is ready.
   func ReadinessCheckHandler() http.HandlerFunc {
       return func(w http.ResponseWriter, r *http.Request) {
           // Initially, readiness will be wired to the ReadinessState
           // in TASK-022 when catalog loading is implemented.
           // For now, return 200 as a placeholder.
           w.Header().Set("Content-Type", "application/json")
           w.WriteHeader(http.StatusOK)
           json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
       }
   }
   ```

   Note: The readiness handler will be updated in TASK-022 to accept `*ReadinessState` and check catalog loading status. For Phase 1, the placeholder returns 200 to allow deployment testing.

2. **Wire handlers in `internal/api/routes.go`** (already done in TASK-003, just verify the routes are registered).

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/go-chi/chi/v5 v5.1+` (already added in TASK-003)

## Acceptance Criteria
1. `GET /healthz` returns HTTP 200 with body `{"status":"ok"}`
2. `GET /readyz` returns HTTP 200 with body `{"status":"ok"}`
3. Both endpoints respond in under 5ms with no external dependencies
4. Content-Type header is `application/json` for both endpoints
5. Both endpoints accept only GET requests (other methods return 405)
6. Unit tests cover both success paths

## Testing Requirements
- **Unit Tests:** Use `httptest.NewRecorder()` to test both handler functions. Verify status codes, response bodies, and Content-Type headers.
- **Integration Tests:** Start server and curl both endpoints from outside the process.
- **Manual Verification:** `curl -v http://localhost:8080/healthz` and `curl -v http://localhost:8080/readyz`

## Files to Create/Modify
- `internal/api/handler.go` — (modify) Implement HealthCheckHandler and ReadinessCheckHandler
- `internal/api/handler_test.go` — (create) Unit tests for health handlers

## Risks & Edge Cases
- The readiness handler must never panic or make external calls — it's called frequently by orchestrators.
- Ensure JSON encoding errors in the health handler don't crash the process (unlikely but handle gracefully).

## Notes
- The readiness endpoint will evolve in TASK-022 to check actual catalog loading status. The current implementation is intentionally simple to unblock deployment pipeline testing.
- Consider adding a `/healthz` response body field for version information (git SHA, build time) in a future iteration.
