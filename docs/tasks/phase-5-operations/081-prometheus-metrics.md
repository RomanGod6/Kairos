# TASK-081: Prometheus Metrics Instrumentation

## Metadata
- **Phase:** 5
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003, TASK-046]
- **Blocks:** None
- **Related:** [TASK-082, TASK-103]

## Objective
Add Prometheus metrics instrumentation across the service: HTTP request latency histograms, classification tier hit rate counters, confidence score distributions, null return rates, Azure AI Foundry call latencies, and request/error counts. Expose metrics via `/metrics` endpoint.

## Design Reference
- See Design Doc §7.3 Observability — Metrics
- See Design Doc §7.3.1 Key Metrics

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (HTTP server)
- TASK-046 complete (pipeline for instrumentation points)

### Implementation Details

1. **Create `internal/api/metrics.go`:**

   ```go
   package api

   import (
       "github.com/prometheus/client_golang/prometheus"
       "github.com/prometheus/client_golang/prometheus/promauto"
   )

   var (
       // HTTP metrics
       HTTPRequestDuration = promauto.NewHistogramVec(
           prometheus.HistogramOpts{
               Name:    "kairos_http_request_duration_seconds",
               Help:    "HTTP request latency in seconds",
               Buckets: []float64{0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5},
           },
           []string{"method", "path", "status"},
       )

       HTTPRequestsTotal = promauto.NewCounterVec(
           prometheus.CounterOpts{
               Name: "kairos_http_requests_total",
               Help: "Total HTTP requests",
           },
           []string{"method", "path", "status"},
       )

       // Classification metrics
       ClassificationTierHits = promauto.NewCounterVec(
           prometheus.CounterOpts{
               Name: "kairos_classification_tier_hits_total",
               Help: "Number of classifications resolved by each tier",
           },
           []string{"tier", "method"},
       )

       ClassificationDuration = promauto.NewHistogramVec(
           prometheus.HistogramOpts{
               Name:    "kairos_classification_duration_seconds",
               Help:    "Classification pipeline latency in seconds",
               Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0},
           },
           []string{"tier"},
       )

       ClassificationConfidence = promauto.NewHistogramVec(
           prometheus.HistogramOpts{
               Name:    "kairos_classification_confidence",
               Help:    "Distribution of classification confidence scores",
               Buckets: []float64{0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0},
           },
           []string{"tier"},
       )

       ClassificationNullTotal = promauto.NewCounter(
           prometheus.CounterOpts{
               Name: "kairos_classification_null_total",
               Help: "Number of classifications returning null (no match)",
           },
       )

       // Azure AI metrics
       AzureAIDuration = promauto.NewHistogramVec(
           prometheus.HistogramOpts{
               Name:    "kairos_azure_ai_duration_seconds",
               Help:    "Azure AI Foundry API call latency in seconds",
               Buckets: []float64{0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0},
           },
           []string{"operation"}, // "embedding" or "completion"
       )

       AzureAIErrorsTotal = promauto.NewCounterVec(
           prometheus.CounterOpts{
               Name: "kairos_azure_ai_errors_total",
               Help: "Azure AI Foundry API errors",
           },
           []string{"operation", "error_type"},
       )
   )
   ```

2. **Create metrics middleware** that wraps HTTP handlers with timing:

   ```go
   func MetricsMiddleware(next http.Handler) http.Handler {
       return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
           start := time.Now()
           ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)

           next.ServeHTTP(ww, r)

           status := strconv.Itoa(ww.Status())
           duration := time.Since(start).Seconds()

           HTTPRequestDuration.WithLabelValues(r.Method, r.URL.Path, status).Observe(duration)
           HTTPRequestsTotal.WithLabelValues(r.Method, r.URL.Path, status).Inc()
       })
   }
   ```

3. **Add instrumentation to pipeline and Azure AI client** — increment counters and observe histograms at appropriate points.

4. **Register `/metrics` endpoint:**
   ```go
   r.Handle("/metrics", promhttp.Handler())
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/prometheus/client_golang v1.20+` (verify latest stable as of March 2026)

## Acceptance Criteria
1. `/metrics` endpoint returns Prometheus text format metrics
2. HTTP request duration histograms track all endpoints with method, path, and status labels
3. Classification tier hit counters increment correctly for each tier
4. Classification confidence histograms capture score distributions
5. Null classification counter increments when no product matches
6. Azure AI call durations are tracked for both embedding and completion operations
7. Azure AI error counters increment by operation and error type
8. Metrics endpoint is unauthenticated (for Prometheus scraping)

## Testing Requirements
- **Unit Tests:** Verify counter increments and histogram observations after mock requests. Test MetricsMiddleware.
- **Integration Tests:** Start server, make requests, scrape /metrics, verify expected metric names and values.
- **Manual Verification:** `curl http://localhost:8080/metrics | grep kairos_`

## Files to Create/Modify
- `internal/api/metrics.go` — (create) Metric definitions and middleware
- `internal/api/routes.go` — (modify) Register /metrics endpoint and MetricsMiddleware
- `internal/classify/pipeline.go` — (modify) Add metric instrumentation
- `internal/azureai/client.go` — (modify) Add timing and error metrics
- `go.mod` — (modify) Add prometheus client dependency

## Risks & Edge Cases
- High-cardinality labels: using `r.URL.Path` as a label could create high cardinality if there are many unique paths. Since Kairos has a fixed route set, this is safe.
- Metric naming follows Prometheus conventions: `snake_case`, prefixed with `kairos_`, suffixed with unit (`_seconds`, `_total`).

## Notes
- These metrics are essential for monitoring SLOs (p95 latency, error rates, tier distribution) in production.
