# TASK-084: Embedding Cache Invalidation and Management

## Metadata
- **Phase:** 5
- **Module:** tier2
- **Priority:** P2-medium
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-044, TASK-083]
- **Blocks:** None
- **Related:** [TASK-024]

## Objective
Implement embedding cache management: invalidate the query embedding cache when the catalog is reloaded, track cache hit rates via metrics, and add an admin endpoint to clear the cache manually.

## Design Reference
- See Design Doc §4.3 Tier 2 (query embedding cache)
- See Design Doc §7.4 Catalog Hot-Reload (cache invalidation)

## Technical Requirements

### Inputs / Prerequisites
- TASK-044 complete (QueryCache exists)
- TASK-083 complete (hot-reload endpoint)

### Implementation Details

1. **Add `Clear()` method to `QueryCache`:**

   ```go
   func (c *QueryCache) Clear() {
       c.mu.Lock()
       defer c.mu.Unlock()
       c.entries = make(map[string][]float64, c.maxSize)
       c.order = nil
   }

   func (c *QueryCache) Size() int {
       c.mu.RLock()
       defer c.mu.RUnlock()
       return len(c.entries)
   }
   ```

2. **Wire cache clearing into catalog reload handler.**

3. **Add cache metrics:**
   ```go
   CacheHitsTotal = promauto.NewCounter(prometheus.CounterOpts{
       Name: "kairos_query_cache_hits_total",
       Help: "Query embedding cache hits",
   })
   CacheMissesTotal = promauto.NewCounter(prometheus.CounterOpts{
       Name: "kairos_query_cache_misses_total",
       Help: "Query embedding cache misses",
   })
   ```

4. **Add admin endpoint:** `POST /admin/clear-cache`

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/prometheus/client_golang v1.20+`

## Acceptance Criteria
1. Query cache is automatically cleared when catalog is reloaded
2. Cache hit/miss metrics are tracked and exposed via `/metrics`
3. `POST /admin/clear-cache` manually clears the query embedding cache
4. Cache size is bounded and LRU eviction works correctly
5. Cache operations are thread-safe

## Testing Requirements
- **Unit Tests:** Test Clear(), Size(), cache hit/miss counting, LRU eviction under concurrent access.
- **Integration Tests:** Reload catalog, verify cache is cleared.
- **Manual Verification:** Check cache hit rate via `/metrics`

## Files to Create/Modify
- `internal/tier2/cache.go` — (modify) Add Clear(), Size(), metrics
- `internal/api/handler.go` — (modify) Add cache clear admin endpoint
- `internal/api/routes.go` — (modify) Register cache clear route

## Risks & Edge Cases
- Clearing the cache during high traffic causes a burst of embedding API calls. This is acceptable — the cache rebuilds within seconds.

## Notes
- Cache size should be configurable. Default 1000 entries is reasonable for typical traffic patterns.
