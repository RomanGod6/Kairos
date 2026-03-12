# TASK-007: Middleware Foundation (Request ID, Logging, Recovery)

## Metadata
- **Phase:** 1
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-002, TASK-003]
- **Blocks:** [TASK-061, TASK-062, TASK-082]
- **Related:** None

## Objective
Create the middleware layer in `internal/api/middleware.go` with foundational middleware: request ID injection, structured request/response logging via zerolog, panic recovery with JSON error responses, and CORS headers. These are the cross-cutting concerns that run on every request.

## Design Reference
- See Design Doc §5.5 Middleware Stack
- See Design Doc §7.3 Observability (request logging)

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (chi router configured)
- TASK-002 complete (config available for log settings)

### Implementation Details

1. **Create `internal/api/middleware.go`:**

   ```go
   package api

   import (
       "net/http"
       "time"

       "github.com/go-chi/chi/v5/middleware"
       "github.com/rs/zerolog"
       "github.com/rs/zerolog/log"
   )

   // RequestLogger returns a zerolog-based request logging middleware.
   func RequestLogger() func(next http.Handler) http.Handler {
       return func(next http.Handler) http.Handler {
           return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
               start := time.Now()
               ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)

               defer func() {
                   log.Info().
                       Str("request_id", middleware.GetReqID(r.Context())).
                       Str("method", r.Method).
                       Str("path", r.URL.Path).
                       Int("status", ww.Status()).
                       Int("bytes", ww.BytesWritten()).
                       Dur("latency", time.Since(start)).
                       Str("remote_addr", r.RemoteAddr).
                       Msg("request completed")
               }()

               next.ServeHTTP(ww, r)
           })
       }
   }

   // JSONRecoverer is a panic recovery middleware that returns JSON error responses
   // instead of plain text.
   func JSONRecoverer(next http.Handler) http.Handler {
       return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
           defer func() {
               if rec := recover(); rec != nil {
                   log.Error().
                       Str("request_id", middleware.GetReqID(r.Context())).
                       Interface("panic", rec).
                       Msg("panic recovered")

                   WriteInternalError(w, r, "internal server error")
               }
           }()
           next.ServeHTTP(w, r)
       })
   }
   ```

2. **Update `internal/api/routes.go`** to use custom middleware instead of chi defaults:
   - Replace `middleware.Recoverer` with `JSONRecoverer`
   - Add `RequestLogger()` to the middleware stack

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/go-chi/chi/v5 v5.1+`
- `github.com/rs/zerolog v1.33+`

## Acceptance Criteria
1. Every request gets a unique request ID accessible via `middleware.GetReqID`
2. Every request/response is logged as structured JSON with method, path, status, latency, and request ID
3. Panics in handlers are caught and return `{"error":{"code":"internal_error","message":"internal server error"}}` with HTTP 500
4. Panic recovery logs the panic details at ERROR level
5. Health check endpoints are also logged (no path exclusions in Phase 1)
6. Unit tests verify logging output and panic recovery behavior

## Testing Requirements
- **Unit Tests:** Test `RequestLogger` with a mock handler — verify log output contains expected fields. Test `JSONRecoverer` with a handler that panics — verify 500 response and JSON body.
- **Integration Tests:** None needed
- **Manual Verification:** Start server, make requests, verify JSON log output on stdout

## Files to Create/Modify
- `internal/api/middleware.go` — (create) Request logging and panic recovery middleware
- `internal/api/middleware_test.go` — (create) Unit tests
- `internal/api/routes.go` — (modify) Wire custom middleware

## Risks & Edge Cases
- Logging large request bodies could be a performance issue — intentionally do not log request/response bodies, only metadata.
- The `middleware.NewWrapResponseWriter` captures the status code written by the handler. If the handler never calls `WriteHeader`, the default is 200.

## Notes
- The request logger logs at INFO level. For production, consider adding a middleware that logs health checks at DEBUG level to reduce noise (deferred to TASK-082).
