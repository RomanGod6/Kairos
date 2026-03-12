# TASK-061: API Key Authentication Middleware

## Metadata
- **Phase:** 4
- **Module:** api
- **Priority:** P0-critical
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003, TASK-006, TASK-007]
- **Blocks:** None
- **Related:** [TASK-062]

## Objective
Implement Bearer token authentication middleware that validates API keys on all `/v1/*` endpoints. Health check endpoints remain unauthenticated. The middleware extracts the `Authorization: Bearer <key>` header and compares against the configured API key using constant-time comparison.

## Design Reference
- See Design Doc §5.5 Middleware Stack — Authentication
- See Design Doc §3 Configuration (KAIROS_API_KEY)

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (chi router and middleware stack)
- TASK-006 complete (WriteUnauthorized error helper)

### Implementation Details

1. **Add to `internal/api/middleware.go`:**

   ```go
   import (
       "crypto/subtle"
       "net/http"
       "strings"
   )

   // AuthMiddleware validates Bearer token authentication.
   func AuthMiddleware(apiKey string) func(http.Handler) http.Handler {
       keyBytes := []byte(apiKey)

       return func(next http.Handler) http.Handler {
           return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
               authHeader := r.Header.Get("Authorization")
               if authHeader == "" {
                   WriteUnauthorized(w, r)
                   return
               }

               parts := strings.SplitN(authHeader, " ", 2)
               if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
                   WriteUnauthorized(w, r)
                   return
               }

               token := []byte(parts[1])
               if subtle.ConstantTimeCompare(token, keyBytes) != 1 {
                   WriteUnauthorized(w, r)
                   return
               }

               next.ServeHTTP(w, r)
           })
       }
   }
   ```

2. **Wire into routes.go** on the `/v1` route group:
   ```go
   r.Route("/v1", func(r chi.Router) {
       r.Use(AuthMiddleware(cfg.Server.APIKey))
       r.Post("/classify", ClassifyHandler(pipeline))
   })
   ```

### Tech Stack & Dependencies
- `go 1.22+` (standard library `crypto/subtle`)

## Acceptance Criteria
1. Requests with valid `Authorization: Bearer <key>` pass through to handlers
2. Requests without `Authorization` header receive HTTP 401 with structured error
3. Requests with invalid token receive HTTP 401
4. Requests with malformed header (no "Bearer" prefix) receive HTTP 401
5. Token comparison uses constant-time algorithm (prevents timing attacks)
6. Health check endpoints (`/healthz`, `/readyz`) are NOT protected by auth
7. Unit tests cover all authentication scenarios

## Testing Requirements
- **Unit Tests:** Test valid token, missing header, wrong token, malformed header, case-insensitive "Bearer"/"bearer".
- **Integration Tests:** None needed
- **Manual Verification:** `curl -H "Authorization: Bearer <key>" http://localhost:8080/v1/classify`

## Files to Create/Modify
- `internal/api/middleware.go` — (modify) Add AuthMiddleware
- `internal/api/middleware_test.go` — (modify) Add auth middleware tests
- `internal/api/routes.go` — (modify) Wire auth middleware on /v1 routes

## Risks & Edge Cases
- Multi-key support: the current design supports a single API key. For multi-tenant use, this would need a key lookup table. Single key is sufficient for v1.
- Empty API key in config: if `KAIROS_API_KEY` is empty, config validation (TASK-002) should reject startup. The middleware must never accept empty Bearer tokens.

## Notes
- Constant-time comparison prevents timing side-channel attacks where an attacker could infer the correct key length or prefix by measuring response times.
