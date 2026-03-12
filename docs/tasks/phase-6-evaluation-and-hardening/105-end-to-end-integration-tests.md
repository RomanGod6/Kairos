# TASK-105: End-to-End Integration Tests

## Metadata
- **Phase:** 6
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-060, TASK-061, TASK-062, TASK-046]
- **Blocks:** None
- **Related:** [TASK-100, TASK-104]

## Objective
Create comprehensive end-to-end integration tests that start the full Kairos server with mock Azure AI backends, send classification requests through the HTTP API, and verify the complete request lifecycle including authentication, rate limiting, classification pipeline, response formatting, and metrics.

## Design Reference
- See Design Doc §9 Evaluation & Testing
- See Design Doc §5 API Contract (expected behavior)

## Technical Requirements

### Inputs / Prerequisites
- All Phase 4 tasks complete (API endpoints)
- TASK-046 complete (pipeline orchestrator)

### Implementation Details

1. **Create `internal/api/integration_test.go`:**

   ```go
   package api_test

   import (
       "bytes"
       "encoding/json"
       "net/http"
       "net/http/httptest"
       "testing"

       "github.com/kaseya/kairos/internal/api"
       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
       "github.com/kaseya/kairos/internal/config"
       // ... tier imports with mocks
   )

   func setupTestServer(t *testing.T) *httptest.Server {
       t.Helper()

       // Load sample catalog
       store := catalog.NewStore()
       if err := store.LoadCatalog("../../data/catalog.json"); err != nil {
           t.Fatalf("loading test catalog: %v", err)
       }

       // Create pipeline with mock Azure AI
       mockEmbedder := &MockEmbedder{/* configured with test vectors */}
       mockCompleter := &MockCompleter{/* configured with test responses */}
       // ... build pipeline

       cfg := &config.Config{
           Server: config.ServerConfig{APIKey: "test-api-key"},
           // ... other test config
       }

       router := api.NewRouter(cfg, pipeline)
       return httptest.NewServer(router)
   }

   func TestClassifyEndToEnd(t *testing.T) {
       srv := setupTestServer(t)
       defer srv.Close()

       tests := []struct {
           name           string
           message        string
           expectedStatus int
           expectedMatch  bool
           expectedProduct string
       }{
           {"keyword match", "help with VSA", 200, true, "kaseya-vsa"},
           {"semantic match", "my endpoints aren't checking in", 200, true, "kaseya-vsa"},
           {"no match", "what's the weather today", 200, false, ""},
           {"empty message", "", 422, false, ""},
       }

       for _, tt := range tests {
           t.Run(tt.name, func(t *testing.T) {
               body, _ := json.Marshal(api.ClassifyRequest{Message: tt.message})
               req, _ := http.NewRequest("POST", srv.URL+"/v1/classify",
                   bytes.NewReader(body))
               req.Header.Set("Content-Type", "application/json")
               req.Header.Set("Authorization", "Bearer test-api-key")

               resp, err := http.DefaultClient.Do(req)
               if err != nil {
                   t.Fatalf("request failed: %v", err)
               }
               defer resp.Body.Close()

               if resp.StatusCode != tt.expectedStatus {
                   t.Errorf("expected status %d, got %d", tt.expectedStatus, resp.StatusCode)
               }

               // Verify response structure and content
               // ...
           })
       }
   }

   func TestAuthenticationEndToEnd(t *testing.T) {
       // Test missing auth, wrong auth, correct auth
   }

   func TestRateLimitingEndToEnd(t *testing.T) {
       // Send burst of requests, verify 429 after limit
   }
   ```

2. **Test scenarios:**
   - Successful Tier 1 classification (keyword match)
   - Successful Tier 2 classification (semantic match)
   - Tier 3 reranker invocation (ambiguous case)
   - Null response (no match)
   - Authentication failure (missing/wrong key)
   - Validation error (empty message)
   - Rate limit exceeded
   - Health check endpoints
   - Version endpoint

### Tech Stack & Dependencies
- `go 1.22+`
- `net/http/httptest` (standard library)

## Acceptance Criteria
1. All integration tests pass with `go test -v ./internal/api/ -run Integration`
2. Tests cover all HTTP status codes the API can return (200, 400, 401, 422, 429, 500)
3. Tests verify JSON response structure matches the API contract
4. Tests run without Azure AI credentials (using mocks)
5. Tests complete in under 30 seconds
6. Race detector passes: `go test -race ./internal/api/`

## Testing Requirements
- **Unit Tests:** N/A — these are the integration tests
- **Integration Tests:** This IS the integration test suite
- **Manual Verification:** Run `go test -v ./internal/api/ -run Integration`

## Files to Create/Modify
- `internal/api/integration_test.go` — (create) End-to-end integration tests
- `internal/api/testutil_test.go` — (create) Test helper functions

## Risks & Edge Cases
- Test data dependency: tests rely on `data/catalog.json` from TASK-023. If the file changes, tests may need updating.
- Mock fidelity: mocked Azure AI responses must be realistic enough to exercise the full pipeline path.

## Notes
- These tests complement the unit tests in each package. They catch integration issues that unit tests miss (e.g., middleware ordering, route configuration, JSON serialization mismatches).
