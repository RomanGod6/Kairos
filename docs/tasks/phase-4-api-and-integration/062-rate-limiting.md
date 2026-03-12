# TASK-062: Rate Limiting Middleware

## Metadata
- **Phase:** 4
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003, TASK-006, TASK-007]
- **Blocks:** None
- **Related:** [TASK-061, TASK-081]

## Objective
Implement rate limiting middleware that enforces 500 requests per minute per API key. Uses a token bucket algorithm with in-memory state. Returns HTTP 429 with structured error and `Retry-After` header when rate limit is exceeded.

## Design Reference
- See Design Doc §5.5 Middleware Stack — Rate Limiting
- See Design Doc §5.4 Error Responses (429 rate limited)
- See Design Doc §3 Configuration (KAIROS_RATE_LIMIT_PER_MIN)

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (chi router)
- TASK-006 complete (WriteRateLimited error helper)

### Implementation Details

1. **Create `internal/api/ratelimit.go`:**

   ```go
   package api

   import (
       "net/http"
       "strconv"
       "sync"
       "time"
   )

   // RateLimiter implements a per-key token bucket rate limiter.
   type RateLimiter struct {
       mu      sync.Mutex
       buckets map[string]*bucket
       rate    int // tokens per minute
       cleanup time.Duration
   }

   type bucket struct {
       tokens    float64
       lastCheck time.Time
   }

   // NewRateLimiter creates a rate limiter with the given requests-per-minute limit.
   func NewRateLimiter(requestsPerMinute int) *RateLimiter {
       rl := &RateLimiter{
           buckets: make(map[string]*bucket),
           rate:    requestsPerMinute,
           cleanup: 10 * time.Minute,
       }
       go rl.cleanupLoop()
       return rl
   }

   // Allow checks if a request from the given key is allowed.
   func (rl *RateLimiter) Allow(key string) bool {
       rl.mu.Lock()
       defer rl.mu.Unlock()

       now := time.Now()
       b, ok := rl.buckets[key]
       if !ok {
           b = &bucket{
               tokens:    float64(rl.rate),
               lastCheck: now,
           }
           rl.buckets[key] = b
       }

       // Refill tokens based on elapsed time
       elapsed := now.Sub(b.lastCheck).Seconds()
       b.tokens += elapsed * float64(rl.rate) / 60.0
       if b.tokens > float64(rl.rate) {
           b.tokens = float64(rl.rate)
       }
       b.lastCheck = now

       if b.tokens >= 1 {
           b.tokens--
           return true
       }

       return false
   }

   func (rl *RateLimiter) cleanupLoop() {
       ticker := time.NewTicker(rl.cleanup)
       defer ticker.Stop()
       for range ticker.C {
           rl.mu.Lock()
           cutoff := time.Now().Add(-rl.cleanup)
           for k, b := range rl.buckets {
               if b.lastCheck.Before(cutoff) {
                   delete(rl.buckets, k)
               }
           }
           rl.mu.Unlock()
       }
   }

   // RateLimitMiddleware creates rate limiting middleware.
   func RateLimitMiddleware(limiter *RateLimiter) func(http.Handler) http.Handler {
       return func(next http.Handler) http.Handler {
           return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
               // Use API key as the rate limit key (from auth header)
               key := r.Header.Get("Authorization")
               if key == "" {
                   key = r.RemoteAddr // Fallback for unauthenticated endpoints
               }

               if !limiter.Allow(key) {
                   w.Header().Set("Retry-After", "60")
                   WriteRateLimited(w, r)
                   return
               }

               next.ServeHTTP(w, r)
           })
       }
   }
   ```

2. **Wire into routes.go** after auth middleware.

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies (standard library only)

## Acceptance Criteria
1. Requests within rate limit (500/min) pass through normally
2. Requests exceeding rate limit receive HTTP 429 with structured error
3. 429 responses include `Retry-After: 60` header
4. Rate limiting is per API key (not global)
5. Token bucket refills correctly over time
6. Stale buckets are cleaned up after 10 minutes of inactivity
7. Rate limiter is thread-safe under concurrent load
8. Unit tests verify token bucket behavior including refill timing

## Testing Requirements
- **Unit Tests:** Test `Allow()` at limit boundary, token refill over time, concurrent access with `-race`. Test cleanup of stale entries.
- **Integration Tests:** Send burst of requests, verify 429 after limit exceeded.
- **Manual Verification:** Use `hey` or `ab` to send 600 requests in 1 minute, verify last 100 get 429s.

## Files to Create/Modify
- `internal/api/ratelimit.go` — (create) Rate limiter implementation and middleware
- `internal/api/ratelimit_test.go` — (create) Unit tests
- `internal/api/routes.go` — (modify) Wire rate limit middleware

## Risks & Edge Cases
- Memory growth: without cleanup, the bucket map grows unbounded. The 10-minute cleanup loop prevents this.
- Clock skew: `time.Now()` is monotonic in Go, so token refill is accurate.
- Single-instance limitation: this is in-memory rate limiting. With multiple instances, each has independent limits. For distributed rate limiting, use Redis (deferred to future iteration).

## Notes
- The 500 req/min limit is configurable via `KAIROS_RATE_LIMIT_PER_MIN` environment variable.
- For v1 with a single instance, in-memory rate limiting is sufficient and avoids external dependencies.
