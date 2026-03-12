# TASK-104: Graceful Degradation Paths

## Metadata
- **Phase:** 6
- **Module:** classify
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-046, TASK-043]
- **Blocks:** None
- **Related:** [TASK-081, TASK-082]

## Objective
Implement and test all graceful degradation paths: (1) Azure AI Foundry embedding endpoint down → skip Tier 2, return Tier 1 result or null with degraded flag; (2) Azure AI Foundry chat completions down → Tier 3 fallback to Tier 2 top match; (3) Both Azure endpoints down → Tier 1 only mode. The service must never crash or return 500 due to external dependency failure.

## Design Reference
- See Design Doc §10.2 Degradation Modes
- See Design Doc §4.4.2 Tier 3 Fallback Behavior
- See Design Doc §7.6 Resilience

## Technical Requirements

### Inputs / Prerequisites
- TASK-046 complete (pipeline orchestrator)
- TASK-043 complete (Azure AI client with error types)

### Implementation Details

1. **Define degradation modes:**

   ```go
   type DegradationMode int

   const (
       ModeFullPipeline  DegradationMode = iota // All tiers operational
       ModeTier1Only                             // Azure AI down, keyword-only
       ModeNoReranker                           // Chat completions down, T1+T2 only
   )
   ```

2. **Implement circuit breaker for Azure AI calls:**

   ```go
   type CircuitBreaker struct {
       mu             sync.Mutex
       failures       int
       threshold      int
       resetTimeout   time.Duration
       lastFailure    time.Time
       state          string // "closed", "open", "half-open"
   }

   func NewCircuitBreaker(threshold int, resetTimeout time.Duration) *CircuitBreaker {
       return &CircuitBreaker{
           threshold:    threshold,
           resetTimeout: resetTimeout,
           state:        "closed",
       }
   }

   func (cb *CircuitBreaker) Allow() bool {
       cb.mu.Lock()
       defer cb.mu.Unlock()

       switch cb.state {
       case "closed":
           return true
       case "open":
           if time.Since(cb.lastFailure) > cb.resetTimeout {
               cb.state = "half-open"
               return true
           }
           return false
       case "half-open":
           return true
       }
       return false
   }

   func (cb *CircuitBreaker) RecordSuccess() {
       cb.mu.Lock()
       defer cb.mu.Unlock()
       cb.failures = 0
       cb.state = "closed"
   }

   func (cb *CircuitBreaker) RecordFailure() {
       cb.mu.Lock()
       defer cb.mu.Unlock()
       cb.failures++
       cb.lastFailure = time.Now()
       if cb.failures >= cb.threshold {
           cb.state = "open"
       }
   }
   ```

3. **Integrate circuit breakers into pipeline:**
   - Embedding circuit breaker: 3 consecutive failures → open for 30 seconds
   - Completion circuit breaker: 3 consecutive failures → open for 30 seconds
   - When open, skip the tier and log at WARN level

4. **Add degradation metrics:**
   ```go
   DegradationModeGauge = promauto.NewGauge(prometheus.GaugeOpts{
       Name: "kairos_degradation_mode",
       Help: "Current degradation mode (0=full, 1=no_reranker, 2=tier1_only)",
   })
   ```

5. **Add response header** `X-Kairos-Degraded: true` when operating in degraded mode.

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/prometheus/client_golang v1.20+`

## Acceptance Criteria
1. When embedding API fails 3 times consecutively, Tier 2 is skipped for 30 seconds
2. When completion API fails 3 times consecutively, Tier 3 is skipped for 30 seconds
3. After circuit breaker reset timeout, the next request attempts the call (half-open)
4. Successful call after half-open closes the circuit breaker
5. Service never returns HTTP 500 due to Azure AI failures — returns degraded results instead
6. Degradation mode is exposed via Prometheus metric
7. Degraded responses include `X-Kairos-Degraded: true` header
8. All degradation paths are logged at WARN level
9. Tier 1-only mode still produces correct results for keyword matches
10. Unit tests cover all circuit breaker state transitions

## Testing Requirements
- **Unit Tests:** Test circuit breaker state machine (closed→open→half-open→closed). Test pipeline with failing mock Embedder/Completer. Test all degradation paths.
- **Integration Tests:** Simulate Azure AI failures (mock server returning 500s), verify graceful degradation.
- **Manual Verification:** Block Azure endpoint in config, send classification requests, verify degraded responses.

## Files to Create/Modify
- `internal/classify/degradation.go` — (create) Circuit breaker and degradation mode types
- `internal/classify/pipeline.go` — (modify) Integrate circuit breakers
- `internal/api/metrics.go` — (modify) Add degradation gauge
- `internal/classify/degradation_test.go` — (create) Circuit breaker tests

## Risks & Edge Cases
- Thundering herd on circuit breaker close: when the breaker transitions to half-open, only one request should probe. The current implementation allows all requests through in half-open, which is acceptable for the expected traffic volume.
- Clock drift: circuit breaker uses `time.Now()` which is monotonic in Go. No risk.
- Cascading degradation: if embeddings are down, Tier 2 is skipped, more traffic goes to Tier 1. Tier 1 only handles ~30% of queries, so null response rate will increase. This is expected and preferable to errors.

## Notes
- This is the most critical resilience feature. The service must be available even when external dependencies fail. "Degraded but available" is always better than "unavailable."
- Consider alerting on degradation mode changes via the Prometheus metric.
