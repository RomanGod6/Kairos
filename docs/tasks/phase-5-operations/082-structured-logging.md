# TASK-082: Structured Logging Enhancement

## Metadata
- **Phase:** 5
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003, TASK-007]
- **Blocks:** None
- **Related:** [TASK-081]

## Objective
Enhance the structured logging setup with zerolog to include: per-request context logging (request ID, session ID), classification pipeline logging (tier, confidence, latency, product matched), Azure AI call logging, and configurable log level filtering for health check endpoints to reduce noise.

## Design Reference
- See Design Doc §7.3 Observability — Logging
- See Design Doc §7.3.2 Log Schema

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (zerolog initialized)
- TASK-007 complete (request logging middleware exists)

### Implementation Details

1. **Add request context logger middleware** that injects a zerolog logger with request ID into the request context:

   ```go
   func ContextLogger() func(next http.Handler) http.Handler {
       return func(next http.Handler) http.Handler {
           return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
               reqID := middleware.GetReqID(r.Context())
               logger := log.With().
                   Str("request_id", reqID).
                   Logger()
               ctx := logger.WithContext(r.Context())
               next.ServeHTTP(w, r.WithContext(ctx))
           })
       }
   }
   ```

2. **Add health check log filtering** — log health checks at TRACE level to reduce noise:

   ```go
   func HealthCheckLogFilter(next http.Handler) http.Handler {
       return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
           if r.URL.Path == "/healthz" || r.URL.Path == "/readyz" {
               // Only log at trace level
               log.Trace().Str("path", r.URL.Path).Msg("health check")
           }
           next.ServeHTTP(w, r)
       })
   }
   ```

3. **Add classification result logging** in the pipeline:
   ```go
   log.Ctx(ctx).Info().
       Str("product_id", result.ProductID).
       Float64("confidence", result.Confidence).
       Str("method", string(result.Method)).
       Int("tier", int(result.Tier)).
       Dur("latency", result.Latency).
       Msg("classification complete")
   ```

4. **Configure zerolog global settings** with timestamp format and caller info in debug mode.

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/rs/zerolog v1.33+`

## Acceptance Criteria
1. Every log line includes `request_id` when within a request context
2. Classification results are logged at INFO level with product, confidence, tier, and latency
3. Health check requests are logged at TRACE level (not visible at INFO)
4. Azure AI calls are logged at DEBUG level with operation type, duration, and success/failure
5. Log output is valid JSON in production mode, human-readable in console mode
6. Log level is configurable via `KAIROS_LOG_LEVEL` environment variable

## Testing Requirements
- **Unit Tests:** Verify context logger injects request ID. Verify health check filtering.
- **Integration Tests:** Start server at DEBUG level, make requests, verify log output contains expected fields.
- **Manual Verification:** Run server with `KAIROS_LOG_LEVEL=debug`, observe logs

## Files to Create/Modify
- `internal/api/middleware.go` — (modify) Add ContextLogger, HealthCheckLogFilter
- `internal/classify/pipeline.go` — (modify) Add result logging with context logger
- `internal/azureai/client.go` — (modify) Add call logging
- `cmd/server/main.go` — (modify) Update logger initialization

## Risks & Edge Cases
- Logging user messages could contain PII. Only log message length, not content, at INFO level. Full message content at DEBUG only.

## Notes
- Structured JSON logs are essential for log aggregation tools (ELK, Datadog, CloudWatch).
