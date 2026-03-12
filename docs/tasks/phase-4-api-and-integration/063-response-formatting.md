# TASK-063: Response Formatting and Content Negotiation

## Metadata
- **Phase:** 4
- **Module:** api
- **Priority:** P2-medium
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-005, TASK-006, TASK-060]
- **Blocks:** None
- **Related:** [TASK-064]

## Objective
Ensure all API responses follow consistent formatting rules: proper Content-Type headers, consistent JSON encoding (no HTML escaping, sorted keys for deterministic output), request body size limits, and proper HTTP status code usage across all endpoints.

## Design Reference
- See Design Doc §5 API Contract (response format requirements)
- See Design Doc §5.4 Error Responses

## Technical Requirements

### Inputs / Prerequisites
- TASK-060 complete (classify endpoint exists)
- TASK-005 complete (response types defined)
- TASK-006 complete (error helpers exist)

### Implementation Details

1. **Create `internal/api/response.go`** with enhanced JSON writing:

   ```go
   package api

   import (
       "bytes"
       "encoding/json"
       "net/http"
   )

   // WriteJSONPretty writes a JSON response with consistent formatting.
   // Disables HTML escaping (important for JSON API responses).
   func WriteJSONPretty(w http.ResponseWriter, status int, data interface{}) {
       var buf bytes.Buffer
       enc := json.NewEncoder(&buf)
       enc.SetEscapeHTML(false)
       if err := enc.Encode(data); err != nil {
           w.Header().Set("Content-Type", "application/json")
           w.WriteHeader(http.StatusInternalServerError)
           w.Write([]byte(`{"error":{"code":"internal_error","message":"response encoding failed"}}`))
           return
       }

       w.Header().Set("Content-Type", "application/json; charset=utf-8")
       w.Header().Set("X-Content-Type-Options", "nosniff")
       w.WriteHeader(status)
       w.Write(buf.Bytes())
   }

   // MaxBodySize is the maximum request body size (64KB).
   const MaxBodySize = 64 * 1024

   // LimitBodyMiddleware limits request body size to prevent memory abuse.
   func LimitBodyMiddleware(next http.Handler) http.Handler {
       return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
           r.Body = http.MaxBytesReader(w, r.Body, MaxBodySize)
           next.ServeHTTP(w, r)
       })
   }
   ```

2. **Update `WriteJSON` in `errors.go`** to use the consistent encoder.

3. **Wire `LimitBodyMiddleware`** into the router for POST endpoints.

### Tech Stack & Dependencies
- `go 1.22+`

## Acceptance Criteria
1. All JSON responses use `Content-Type: application/json; charset=utf-8`
2. JSON encoding does not HTML-escape characters (e.g., `<`, `>`, `&`)
3. `X-Content-Type-Options: nosniff` header is set on all responses
4. Request bodies over 64KB are rejected with HTTP 413
5. Error response for oversized body is structured JSON
6. All response formatting is consistent across classify, health, and error responses

## Testing Requirements
- **Unit Tests:** Test WriteJSONPretty with various data types. Test LimitBodyMiddleware with oversized request. Test HTML escaping is disabled.
- **Integration Tests:** None needed
- **Manual Verification:** Verify response headers with `curl -v`

## Files to Create/Modify
- `internal/api/response.go` — (create) Enhanced response formatting
- `internal/api/errors.go` — (modify) Update WriteJSON to use consistent encoder
- `internal/api/routes.go` — (modify) Wire LimitBodyMiddleware
- `internal/api/response_test.go` — (create) Tests

## Risks & Edge Cases
- `http.MaxBytesReader` produces a specific error type when exceeded. The handler must check for this error and return 413 instead of 400.

## Notes
- These are small but important details for API correctness and security compliance.
