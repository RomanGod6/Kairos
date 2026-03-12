# TASK-046: Pipeline Orchestrator

## Metadata
- **Phase:** 3
- **Module:** classify
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010, TASK-040, TASK-041, TASK-042, TASK-044, TASK-045]
- **Blocks:** [TASK-060]
- **Related:** [TASK-005]

## Objective
Implement the pipeline orchestrator that chains Tier 1 → Tier 2 → Tier 3 together with short-circuit returns, confidence threshold checks, and unified result formatting. This is the core entry point that the API handler calls to classify a user message.

## Design Reference
- See Design Doc §4.1 Pipeline Orchestrator
- See Design Doc §4.1.1 Short-Circuit Logic
- See Design Doc §4.1.2 Result Formatting

## Technical Requirements

### Inputs / Prerequisites
- All tier implementations complete (TASK-041, TASK-042, TASK-044, TASK-045)
- TASK-040 complete (preprocessor)
- TASK-010 complete (Result type)

### Implementation Details

1. **Create `internal/classify/pipeline.go`:**

   ```go
   package classify

   import (
       "context"
       "time"

       "github.com/kaseya/kairos/internal/preprocess"
       "github.com/kaseya/kairos/internal/tier1"
       "github.com/kaseya/kairos/internal/tier2"
       "github.com/kaseya/kairos/internal/tier3"
       "github.com/rs/zerolog/log"
   )

   // Pipeline orchestrates the three-tier classification process.
   type Pipeline struct {
       keywordMatcher  *tier1.Matcher
       semanticMatcher *tier2.SemanticMatcher
       reranker        *tier3.Reranker
   }

   // NewPipeline creates a classification pipeline with all three tiers.
   func NewPipeline(keyword *tier1.Matcher, semantic *tier2.SemanticMatcher, reranker *tier3.Reranker) *Pipeline {
       return &Pipeline{
           keywordMatcher:  keyword,
           semanticMatcher: semantic,
           reranker:        reranker,
       }
   }

   // Classify runs the full classification pipeline for a user message.
   func (p *Pipeline) Classify(ctx context.Context, message string) *Result {
       start := time.Now()

       // Step 1: Preprocess
       normalized := preprocess.NormalizeQuery(message)
       if normalized == "" {
           return &Result{
               Method:  MethodNone,
               Tier:    TierNone,
               Latency: time.Since(start),
               Reason:  "empty message after normalization",
           }
       }

       // Step 2: Tier 1 — Exact keyword match
       t1Result := p.keywordMatcher.Match(normalized)
       if t1Result.Matched {
           log.Debug().
               Str("product_id", t1Result.ProductID).
               Float64("confidence", t1Result.Confidence).
               Msg("Tier 1 exact match")
           return p.tierResultToResult(t1Result, Tier1, time.Since(start))
       }

       // Step 3: Tier 1 — Fuzzy keyword match
       t1Fuzzy := p.keywordMatcher.FuzzyMatch(normalized)
       if t1Fuzzy.Matched {
           log.Debug().
               Str("product_id", t1Fuzzy.ProductID).
               Float64("confidence", t1Fuzzy.Confidence).
               Msg("Tier 1 fuzzy match")
           return p.tierResultToResult(t1Fuzzy, Tier1, time.Since(start))
       }

       // Step 4: Tier 2 — Semantic embedding match
       t2Result, err := p.semanticMatcher.Match(ctx, normalized)
       if err != nil {
           log.Error().Err(err).Msg("Tier 2 semantic match failed")
           return &Result{
               Method:  MethodNone,
               Tier:    Tier2,
               Latency: time.Since(start),
               Reason:  "semantic matching unavailable: " + err.Error(),
           }
       }

       if t2Result.Matched {
           log.Debug().
               Str("product_id", t2Result.ProductID).
               Float64("confidence", t2Result.Confidence).
               Msg("Tier 2 semantic match")
           return p.tierResultToResult(t2Result, Tier2, time.Since(start))
       }

       // Step 5: Tier 3 — LLM reranker (only if ambiguous)
       if t2Result.Ambiguous && p.reranker != nil {
           log.Debug().Msg("Tier 2 ambiguous, escalating to Tier 3 reranker")

           t3Result, err := p.reranker.Rerank(ctx, normalized, t2Result.Candidates)
           if err != nil {
               log.Error().Err(err).Msg("Tier 3 reranker failed")
               // Fall through to return no-match with Tier 2 candidates
           } else if t3Result.Matched {
               log.Debug().
                   Str("product_id", t3Result.ProductID).
                   Float64("confidence", t3Result.Confidence).
                   Msg("Tier 3 reranker match")
               return p.tierResultToResult(t3Result, Tier3, time.Since(start))
           }
       }

       // Step 6: No match — return null with top candidates for diagnostics
       result := &Result{
           Method:  MethodNone,
           Tier:    TierNone,
           Latency: time.Since(start),
           Reason:  "No product matched above confidence threshold",
       }
       if t2Result != nil && len(t2Result.Candidates) > 0 {
           for _, c := range t2Result.Candidates {
               if len(result.TopCandidates) >= 3 {
                   break
               }
               result.TopCandidates = append(result.TopCandidates, Candidate{
                   ProductID:  c.ProductID,
                   Confidence: c.Score,
               })
           }
       }

       return result
   }

   // tierResultToResult converts a tier-specific result to the unified Result type.
   func (p *Pipeline) tierResultToResult(tr *TierResult, tier Tier, latency time.Duration) *Result {
       result := &Result{
           ProductID:  tr.ProductID,
           Confidence: tr.Confidence,
           Method:     tr.Method,
           Tier:       tier,
           Latency:    latency,
       }

       // Look up full product details from the top candidate
       for _, c := range tr.Candidates {
           if c.ProductID == tr.ProductID {
               result.ProductName = c.ProductName
               result.Category = c.Category
               break
           }
       }

       // Add alternatives (top candidates excluding the match)
       for _, c := range tr.Candidates {
           if c.ProductID != tr.ProductID && len(result.Alternatives) < 3 {
               result.Alternatives = append(result.Alternatives, Alternative{
                   ProductID:  c.ProductID,
                   Confidence: c.Score,
               })
           }
       }

       return result
   }
   ```

2. **Wire the pipeline in `cmd/server/main.go`:**
   - Create Azure AI client
   - Create Tier 1 matcher, Tier 2 semantic matcher, Tier 3 reranker
   - Create Pipeline with all three tiers
   - Pass Pipeline to the API handler (TASK-060)

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/rs/zerolog v1.33+`

## Acceptance Criteria
1. Tier 1 exact match short-circuits — Tiers 2 and 3 are never called
2. Tier 1 fuzzy match short-circuits — Tiers 2 and 3 are never called
3. Tier 2 confident match short-circuits — Tier 3 is never called
4. Tier 2 ambiguous result triggers Tier 3 reranker
5. Tier 2 no-match skips Tier 3 and returns null result with candidates
6. Tier 2 failure (embedding API down) returns error result without crashing
7. Tier 3 failure falls back gracefully (logs warning, returns degraded result or null)
8. Result always includes latency measurement from pipeline entry to exit
9. Null results include up to 3 top candidates for diagnostics
10. Unit test coverage ≥ 90% using mock tiers

## Testing Requirements
- **Unit Tests:** Create mock implementations of Matcher, SemanticMatcher, and Reranker. Test every flow path: T1 exact hit, T1 fuzzy hit, T2 confident hit, T2 ambiguous → T3 hit, T2 ambiguous → T3 miss, T2 no match, T2 error, T3 error with fallback, empty input.
- **Integration Tests:** Wire real tier implementations with sample catalog data and verify end-to-end flow.
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/classify/pipeline.go` — (create) Pipeline orchestrator
- `internal/classify/pipeline_test.go` — (create) Comprehensive unit tests
- `cmd/server/main.go` — (modify) Wire pipeline creation at startup

## Risks & Edge Cases
- Context cancellation: if the HTTP request context is cancelled (client disconnect), all tier calls should stop immediately. The `ctx` parameter propagates cancellation correctly.
- Nil reranker: if Tier 3 is disabled (no Azure AI config for completions), `p.reranker` is nil. The orchestrator checks for nil before calling.
- Empty normalized input: the preprocessor may reduce input to empty. Return immediately with "empty message" reason.

## Notes
- The pipeline is stateless — all state lives in the catalog Store and tier implementations. This makes it safe for concurrent use by multiple HTTP handlers.
- Debug-level logging in the pipeline aids troubleshooting without impacting production performance (filtered by log level).
