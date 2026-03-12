# TASK-044: Tier 2 — Cosine Similarity and Multi-Anchor Scoring

## Metadata
- **Phase:** 3
- **Module:** tier2
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010, TASK-022, TASK-043]
- **Blocks:** [TASK-046]
- **Related:** [TASK-024]

## Objective
Implement the Tier 2 semantic similarity engine: embed the user query via Azure AI Foundry, compute cosine similarity against all pre-computed product anchor vectors, apply the multi-anchor max-score-per-product strategy, and determine whether the result is a confident match, ambiguous (send to Tier 3), or no match.

## Design Reference
- See Design Doc §4.3 Tier 2: Semantic Embedding Match
- See Design Doc §4.3.1 Multi-Anchor Strategy
- See Design Doc §4.3.2 Confidence Gap Analysis

## Technical Requirements

### Inputs / Prerequisites
- TASK-043 complete (Azure AI Foundry Embedder interface)
- TASK-022 complete (catalog Store with loaded embeddings)
- TASK-010 complete (TierResult, ScoredCandidate types)

### Implementation Details

1. **Create `internal/tier2/similarity.go`:**

   ```go
   package tier2

   import "math"

   // CosineSimilarity computes the cosine similarity between two vectors.
   // Returns a value between -1 and 1 (1 = identical direction).
   func CosineSimilarity(a, b []float64) float64 {
       if len(a) != len(b) || len(a) == 0 {
           return 0
       }

       var dotProduct, normA, normB float64
       for i := range a {
           dotProduct += a[i] * b[i]
           normA += a[i] * a[i]
           normB += b[i] * b[i]
       }

       denominator := math.Sqrt(normA) * math.Sqrt(normB)
       if denominator == 0 {
           return 0
       }

       return dotProduct / denominator
   }
   ```

2. **Create `internal/tier2/embedder.go`:**

   ```go
   package tier2

   import (
       "context"
       "fmt"
       "sort"

       "github.com/kaseya/kairos/internal/azureai"
       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
       "github.com/kaseya/kairos/internal/config"
   )

   // SemanticMatcher performs Tier 2 semantic embedding matching.
   type SemanticMatcher struct {
       embedder   azureai.Embedder
       store      *catalog.Store
       thresholds config.ThresholdConfig
   }

   // NewSemanticMatcher creates a Tier 2 matcher.
   func NewSemanticMatcher(embedder azureai.Embedder, store *catalog.Store, thresholds config.ThresholdConfig) *SemanticMatcher {
       return &SemanticMatcher{
           embedder:   embedder,
           store:      store,
           thresholds: thresholds,
       }
   }

   // Match embeds the user query and compares against all product anchors.
   func (m *SemanticMatcher) Match(ctx context.Context, normalizedQuery string) (*classify.TierResult, error) {
       // 1. Embed the user query
       vectors, err := m.embedder.Embed(ctx, []string{normalizedQuery})
       if err != nil {
           return nil, fmt.Errorf("embedding query: %w", err)
       }
       queryVec := vectors[0]

       // 2. Score every product using max-anchor strategy
       products := m.store.GetAllProducts()
       scored := make([]classify.ScoredCandidate, 0, len(products))

       for _, p := range products {
           anchors := m.store.GetEmbeddings(p.ProductID)
           if len(anchors) == 0 {
               continue
           }

           // Max similarity across all anchors for this product
           maxSim := -1.0
           for _, anchor := range anchors {
               sim := CosineSimilarity(queryVec, anchor.Vector)
               if sim > maxSim {
                   maxSim = sim
               }
           }

           scored = append(scored, classify.ScoredCandidate{
               ProductID:   p.ProductID,
               ProductName: p.ProductName,
               Category:    p.Category,
               Score:       maxSim,
           })
       }

       // 3. Sort by score descending
       sort.Slice(scored, func(i, j int) bool {
           return scored[i].Score > scored[j].Score
       })

       // 4. Determine result based on thresholds
       if len(scored) == 0 {
           return &classify.TierResult{
               Matched: false,
               Method:  classify.MethodSemantic,
           }, nil
       }

       top := scored[0]
       gap := 0.0
       if len(scored) > 1 {
           gap = top.Score - scored[1].Score
       } else {
           gap = 1.0 // Only one product, no ambiguity
       }

       result := &classify.TierResult{
           Candidates: scored,
           Method:     classify.MethodSemantic,
       }

       // Keep top 5 candidates for diagnostics
       if len(result.Candidates) > 5 {
           result.Candidates = result.Candidates[:5]
       }

       switch {
       case top.Score >= m.thresholds.SemanticHighThreshold && gap >= m.thresholds.SemanticMinGap:
           // Strong match with clear gap
           result.Matched = true
           result.ProductID = top.ProductID
           result.Confidence = top.Score

       case top.Score >= m.thresholds.SemanticAmbiguousThreshold && gap < m.thresholds.SemanticMinGap:
           // Above minimum but too close — ambiguous, send to Tier 3
           result.Matched = false
           result.Ambiguous = true
           result.ProductID = top.ProductID
           result.Confidence = top.Score

       default:
           // Below threshold — no match
           result.Matched = false
           result.Ambiguous = false
       }

       return result, nil
   }
   ```

3. **Create `internal/tier2/cache.go`** for embedding cache management:

   ```go
   package tier2

   import "sync"

   // QueryCache caches recent query embeddings to avoid re-embedding
   // identical or very similar queries. LRU with configurable max size.
   type QueryCache struct {
       mu      sync.RWMutex
       entries map[string][]float64
       order   []string
       maxSize int
   }

   func NewQueryCache(maxSize int) *QueryCache {
       return &QueryCache{
           entries: make(map[string][]float64, maxSize),
           maxSize: maxSize,
       }
   }

   func (c *QueryCache) Get(key string) ([]float64, bool) {
       c.mu.RLock()
       defer c.mu.RUnlock()
       v, ok := c.entries[key]
       return v, ok
   }

   func (c *QueryCache) Put(key string, vector []float64) {
       c.mu.Lock()
       defer c.mu.Unlock()
       if _, exists := c.entries[key]; exists {
           return
       }
       if len(c.entries) >= c.maxSize {
           oldest := c.order[0]
           c.order = c.order[1:]
           delete(c.entries, oldest)
       }
       c.entries[key] = vector
       c.order = append(c.order, key)
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies beyond Azure AI client (TASK-043)

## Acceptance Criteria
1. `CosineSimilarity` returns 1.0 for identical vectors, 0.0 for orthogonal, -1.0 for opposite
2. `CosineSimilarity` handles zero vectors and mismatched lengths gracefully (returns 0)
3. Multi-anchor scoring uses max similarity across all anchors per product
4. Results are sorted by score descending
5. Strong match (score ≥ 0.78, gap ≥ 0.08) → `Matched: true`
6. Ambiguous match (score ≥ 0.65, gap < 0.08) → `Matched: false, Ambiguous: true`
7. No match (score < 0.65) → `Matched: false, Ambiguous: false`
8. Query cache prevents duplicate embedding API calls for identical queries
9. Unit test coverage ≥ 90% (using mock Embedder)
10. Cosine similarity benchmark: < 1ms for 44 products × 5 anchors × 1536 dimensions

## Testing Requirements
- **Unit Tests:** Test `CosineSimilarity` with known vectors. Test `Match` with mock `Embedder` returning controlled vectors. Test all three threshold branches. Test `QueryCache` LRU eviction. Benchmark cosine similarity.
- **Integration Tests:** Test with real embeddings from TASK-024 sample data.
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/tier2/similarity.go` — (create) Cosine similarity function
- `internal/tier2/embedder.go` — (create) Semantic matcher with multi-anchor scoring
- `internal/tier2/cache.go` — (create) Query embedding LRU cache
- `internal/tier2/similarity_test.go` — (create) Unit tests and benchmarks
- `internal/tier2/embedder_test.go` — (create) Unit tests with mock Embedder

## Risks & Edge Cases
- Floating point precision: cosine similarity may return values slightly above 1.0 due to rounding. Clamp to [-1, 1].
- Empty embedding vectors (all zeros) from a bad model response: `CosineSimilarity` returns 0, which is below threshold. Safe.
- If the embedder returns an error (Azure down), the entire Tier 2 fails. The pipeline orchestrator handles fallback (TASK-046).
- Cache key should be the normalized query string. Queries that normalize to the same string share cache entries.

## Notes
- The cosine similarity computation is CPU-bound and runs in-process. For 44 products × 5 anchors = 220 comparisons × 1536 dimensions, this is ~340K float64 multiplications — well under 1ms on modern hardware.
- The `QueryCache` is a simple LRU. A production optimization would be a time-based TTL cache, but LRU is sufficient for v1.
