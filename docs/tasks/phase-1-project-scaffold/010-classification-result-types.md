# TASK-010: Classification Result and Pipeline Types

## Metadata
- **Phase:** 1
- **Module:** classify
- **Priority:** P1-high
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001]
- **Blocks:** [TASK-040, TASK-041, TASK-042, TASK-045, TASK-046]
- **Related:** [TASK-005, TASK-011]

## Objective
Define the internal classification result types used by the pipeline orchestrator and all three tiers. These are the internal data structures (distinct from API response types) that flow through the classification pipeline.

## Design Reference
- See Design Doc §4 Classification Pipeline (three-tier result flow)
- See Design Doc §4.1 Pipeline Orchestrator

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (Go module)

### Implementation Details

1. **Create `internal/classify/result.go`:**

   ```go
   package classify

   import "time"

   // Method represents the classification method that produced a result.
   type Method string

   const (
       MethodKeywordExact Method = "keyword_exact"
       MethodKeywordFuzzy Method = "keyword_fuzzy"
       MethodSemantic     Method = "semantic"
       MethodReranker     Method = "reranker"
       MethodNone         Method = "none"
   )

   // Tier represents which classification tier produced the result.
   type Tier int

   const (
       TierNone Tier = 0
       Tier1    Tier = 1
       Tier2    Tier = 2
       Tier3    Tier = 3
   )

   // Result is the unified output of the classification pipeline.
   type Result struct {
       // ProductID is the matched product identifier, empty if no match.
       ProductID string

       // ProductName is the human-readable product name.
       ProductName string

       // Category is the product category (e.g., "RMM", "PSA", "Backup").
       Category string

       // Confidence is the classification confidence score (0.0 to 1.0).
       Confidence float64

       // Method indicates which classification approach produced this result.
       Method Method

       // Tier indicates which tier (1, 2, or 3) produced this result.
       Tier Tier

       // Latency is the total time spent in classification.
       Latency time.Duration

       // Alternatives are runner-up matches (may be empty).
       Alternatives []Alternative

       // Reason is populated when Product is empty (no match).
       Reason string

       // TopCandidates is populated for null responses to show what was closest.
       TopCandidates []Candidate
   }

   // Alternative is a runner-up product match from the pipeline.
   type Alternative struct {
       ProductID  string
       Confidence float64
   }

   // Candidate represents a below-threshold match for diagnostic purposes.
   type Candidate struct {
       ProductID  string
       Confidence float64
   }

   // IsMatch returns true if the result contains a matched product.
   func (r *Result) IsMatch() bool {
       return r.ProductID != ""
   }

   // TierResult is the output of an individual tier (Tier 1, 2, or 3).
   // The pipeline orchestrator collects these and decides whether to
   // short-circuit or continue to the next tier.
   type TierResult struct {
       // Matched is true if this tier produced a confident match.
       Matched bool

       // ProductID of the best match (if Matched is true).
       ProductID string

       // Confidence score of the best match.
       Confidence float64

       // Candidates are the top-N matches from this tier, ordered by confidence.
       Candidates []ScoredCandidate

       // Method used by this tier.
       Method Method

       // Ambiguous is true when Tier 2 detects a close race between top candidates.
       Ambiguous bool
   }

   // ScoredCandidate is a product with its similarity/confidence score.
   type ScoredCandidate struct {
       ProductID   string
       ProductName string
       Category    string
       Score       float64
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies

## Acceptance Criteria
1. All classification result types compile without errors
2. `Result.IsMatch()` correctly distinguishes match vs no-match
3. `TierResult.Ambiguous` flag is available for Tier 2 → Tier 3 escalation logic
4. `ScoredCandidate` carries enough info to populate both `Result` and API response types
5. All types are in the `classify` package (not `api`) to keep internal and external representations separate
6. Method and Tier constants are exhaustive for all pipeline paths

## Testing Requirements
- **Unit Tests:** Test `IsMatch()` with empty and populated results. Test that all Method/Tier constants are distinct.
- **Integration Tests:** None — data types only
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/classify/result.go` — (create) Internal classification result types

## Risks & Edge Cases
- Ensure `Latency` is measured end-to-end (from pipeline entry to exit), not per-tier. Individual tier latencies can be tracked via metrics (TASK-081).
- The `Alternatives` slice should be capped to a reasonable limit (e.g., top 3) to prevent unbounded memory in edge cases.

## Notes
- These types are internal to the service. The API response types in `internal/api/types.go` (TASK-005) are the external contract. The pipeline orchestrator (TASK-046) will translate between them.
