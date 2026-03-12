# TASK-006: Structured JSON Error Response Helpers

## Metadata
- **Phase:** 1
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-002, TASK-005]
- **Blocks:** [TASK-060, TASK-061, TASK-062]
- **Related:** [TASK-063]

## Objective
Create reusable helper functions for writing consistent JSON error responses across all endpoints. Every error the API returns must use the same envelope format with appropriate HTTP status codes and machine-readable error codes.

## Design Reference
- See Design Doc §5.4 Error Responses

## Technical Requirements

### Inputs / Prerequisites
- TASK-005 complete (ErrorResponse type defined)

### Implementation Details

1. **Create `internal/api/errors.go`:**

   ```go
   package api

   import (
       "encoding/json"
       "net/http"

       "github.com/go-chi/chi/v5/middleware"
   )

   // Standard error codes
   const (
       ErrCodeBadRequest       = "bad_request"
       ErrCodeUnauthorized     = "unauthorized"
       ErrCodeForbidden        = "forbidden"
       ErrCodeNotFound         = "not_found"
       ErrCodeRateLimited      = "rate_limited"
       ErrCodeInternalError    = "internal_error"
       ErrCodeServiceDegraded  = "service_degraded"
       ErrCodeValidationFailed = "validation_failed"
   )

   // WriteError writes a structured JSON error response.
   func WriteError(w http.ResponseWriter, r *http.Request, status int, code, message string) {
       reqID := middleware.GetReqID(r.Context())
       resp := ErrorResponse{
           Error: ErrorDetail{
               Code:    code,
               Message: message,
           },
           RequestID: reqID,
       }
       w.Header().Set("Content-Type", "application/json")
       w.WriteHeader(status)
       json.NewEncoder(w).Encode(resp)
   }

   // WriteBadRequest writes a 400 error response.
   func WriteBadRequest(w http.ResponseWriter, r *http.Request, message string) {
       WriteError(w, r, http.StatusBadRequest, ErrCodeBadRequest, message)
   }

   // WriteUnauthorized writes a 401 error response.
   func WriteUnauthorized(w http.ResponseWriter, r *http.Request) {
       WriteError(w, r, http.StatusUnauthorized, ErrCodeUnauthorized, "invalid or missing API key")
   }

   // WriteRateLimited writes a 429 error response.
   func WriteRateLimited(w http.ResponseWriter, r *http.Request) {
       WriteError(w, r, http.StatusTooManyRequests, ErrCodeRateLimited, "rate limit exceeded")
   }

   // WriteInternalError writes a 500 error response.
   // The message parameter should be safe to expose to clients (no internal details).
   func WriteInternalError(w http.ResponseWriter, r *http.Request, message string) {
       WriteError(w, r, http.StatusInternalServerError, ErrCodeInternalError, message)
   }

   // WriteValidationError writes a 422 error response.
   func WriteValidationError(w http.ResponseWriter, r *http.Request, message string) {
       WriteError(w, r, http.StatusUnprocessableEntity, ErrCodeValidationFailed, message)
   }

   // WriteJSON writes a successful JSON response.
   func WriteJSON(w http.ResponseWriter, status int, data interface{}) {
       w.Header().Set("Content-Type", "application/json")
       w.WriteHeader(status)
       json.NewEncoder(w).Encode(data)
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/go-chi/chi/v5 v5.1+` (for `middleware.GetReqID`)

## Acceptance Criteria
1. `WriteError` produces JSON matching the `ErrorResponse` structure with the correct HTTP status code
2. All convenience functions (`WriteBadRequest`, `WriteUnauthorized`, etc.) set the correct status code and error code
3. Every error response includes the request ID from chi middleware
4. `Content-Type` is always `application/json` for error responses
5. `WriteJSON` works for any serializable value and sets correct Content-Type
6. Unit tests cover all error helper functions

## Testing Requirements
- **Unit Tests:** Use `httptest.NewRecorder` to call each helper, verify status code, Content-Type header, and JSON body structure.
- **Integration Tests:** None needed
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/api/errors.go` — (create) Error response helpers
- `internal/api/errors_test.go` — (create) Unit tests

## Risks & Edge Cases
- JSON encoding failure in `WriteError` itself: if `json.Encoder.Encode` fails (extremely rare), the client gets a partial response. Accept this risk — it's essentially impossible for these simple structs.
- Ensure error messages passed to `WriteInternalError` never contain stack traces or internal details that could leak information.

## Notes
- The `WriteError` function deliberately does not log — logging is handled by the request logging middleware (TASK-082). This keeps concerns separated.
