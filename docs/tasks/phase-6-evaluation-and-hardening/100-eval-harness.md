# TASK-100: Evaluation Harness for Classification Accuracy

## Metadata
- **Phase:** 6
- **Module:** scripts
- **Priority:** P0-critical
- **Estimated Effort:** 3-5 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-046, TASK-023]
- **Blocks:** [TASK-101]
- **Related:** [TASK-103]

## Objective
Build an evaluation harness (`scripts/eval/`) that measures classification accuracy against a labeled query dataset. The harness runs queries through the pipeline, compares predicted products to ground truth labels, and reports top-1 accuracy, per-tier breakdown, confusion patterns, and confidence calibration metrics. This is the primary tool for validating and tuning the classification system.

## Design Reference
- See Design Doc §9 Evaluation & Accuracy
- See Design Doc §9.1 Labeled Query Format
- See Design Doc §9.2 Accuracy Metrics

## Technical Requirements

### Inputs / Prerequisites
- TASK-046 complete (pipeline to evaluate)
- TASK-023 complete (sample catalog data for initial testing)

### Implementation Details

1. **Create labeled query test data format** at `scripts/eval/testdata/labeled-queries.json`:

   ```json
   {
     "version": "1.0.0",
     "queries": [
       {
         "id": "q001",
         "message": "my endpoints aren't checking in",
         "expected_product_id": "kaseya-vsa",
         "expected_tier": 2,
         "difficulty": "easy",
         "tags": ["rmm", "agent-status"]
       },
       {
         "id": "q002",
         "message": "VSA",
         "expected_product_id": "kaseya-vsa",
         "expected_tier": 1,
         "difficulty": "easy",
         "tags": ["keyword", "exact-match"]
       },
       {
         "id": "q003",
         "message": "I need to set up a backup for my client's server",
         "expected_product_id": "datto-bcdr",
         "expected_tier": 2,
         "difficulty": "medium",
         "tags": ["backup", "ambiguous"]
       },
       {
         "id": "q004",
         "message": "help",
         "expected_product_id": "",
         "expected_tier": 0,
         "difficulty": "hard",
         "tags": ["null-response", "vague"]
       }
     ]
   }
   ```

2. **Create `scripts/eval/eval.go`:**

   ```go
   package main

   import (
       "context"
       "encoding/json"
       "flag"
       "fmt"
       "os"
       "strings"
       "time"

       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
       // ... other imports
   )

   type LabeledQuery struct {
       ID                string   `json:"id"`
       Message           string   `json:"message"`
       ExpectedProductID string   `json:"expected_product_id"`
       ExpectedTier      int      `json:"expected_tier"`
       Difficulty        string   `json:"difficulty"`
       Tags              []string `json:"tags"`
   }

   type EvalResult struct {
       QueryID           string  `json:"query_id"`
       Message           string  `json:"message"`
       ExpectedProduct   string  `json:"expected_product"`
       PredictedProduct  string  `json:"predicted_product"`
       Confidence        float64 `json:"confidence"`
       Tier              int     `json:"tier"`
       Correct           bool    `json:"correct"`
       LatencyMs         int64   `json:"latency_ms"`
   }

   type EvalReport struct {
       TotalQueries      int     `json:"total_queries"`
       Top1Accuracy      float64 `json:"top1_accuracy"`
       TierBreakdown     map[string]TierStats `json:"tier_breakdown"`
       NullAccuracy      float64 `json:"null_accuracy"`
       AvgConfidence     float64 `json:"avg_confidence"`
       AvgLatencyMs      float64 `json:"avg_latency_ms"`
       P95LatencyMs      float64 `json:"p95_latency_ms"`
       ConfusionPairs    []ConfusionPair `json:"confusion_pairs"`
       ByDifficulty      map[string]float64 `json:"by_difficulty"`
   }

   type TierStats struct {
       Queries  int     `json:"queries"`
       Correct  int     `json:"correct"`
       Accuracy float64 `json:"accuracy"`
   }

   type ConfusionPair struct {
       Expected  string `json:"expected"`
       Predicted string `json:"predicted"`
       Count     int    `json:"count"`
   }
   ```

3. **Evaluation flow:**
   - Load labeled queries from JSON
   - Initialize classification pipeline (with or without Azure AI — use mock for offline eval)
   - Run each query through the pipeline
   - Compare predicted product_id against expected
   - Aggregate results into the EvalReport
   - Print summary and write detailed results to `scripts/eval/results/eval-report.json`

4. **Add Makefile target:**
   ```makefile
   eval:
   	go run ./scripts/eval/ -queries scripts/eval/testdata/labeled-queries.json -output scripts/eval/results/
   ```

5. **Support `--offline` mode** that uses pre-computed embeddings (no Azure API calls) for fast local evaluation.

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies

## Acceptance Criteria
1. Running `make eval` produces a classification accuracy report
2. Report includes top-1 accuracy as a percentage
3. Report includes per-tier accuracy breakdown (Tier 1, 2, 3)
4. Report identifies confusion pairs (most commonly confused product pairs)
5. Report includes latency statistics (average, p95)
6. Report includes accuracy by difficulty level
7. Null responses are evaluated correctly (expected null vs unexpected null)
8. Offline mode runs without Azure AI credentials
9. Labeled query format supports at least 200 test queries
10. Results are written to a JSON file for trend tracking

## Testing Requirements
- **Unit Tests:** Test accuracy calculation, confusion pair identification, report generation with mock results.
- **Integration Tests:** Run eval with sample catalog and 10-20 test queries.
- **Manual Verification:** Review eval report for accuracy, check confusion pairs make sense.

## Files to Create/Modify
- `scripts/eval/eval.go` — (create) Evaluation harness
- `scripts/eval/testdata/labeled-queries.json` — (create) Initial labeled test set (50+ queries)
- `Makefile` — (modify) Add `eval` target

## Risks & Edge Cases
- Evaluation with real Azure AI calls is expensive for large test sets. The offline mode mitigates this.
- Labeled query quality directly impacts evaluation usefulness. Start with 50 well-labeled queries and grow.
- Some queries are genuinely ambiguous (reasonable annotators disagree). Track inter-annotator agreement if expanding the dataset.

## Notes
- Target accuracy: ≥ 85% top-1 for the initial labeled set, ≥ 90% after threshold tuning (TASK-101).
- The eval harness will be run in CI after threshold or catalog changes to catch regressions.
