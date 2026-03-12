# TASK-101: Threshold Tuning Tool

## Metadata
- **Phase:** 6
- **Module:** scripts
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-100]
- **Blocks:** None
- **Related:** [TASK-002]

## Objective
Build a threshold tuning script that runs the evaluation harness across a grid of threshold values and identifies the optimal configuration that maximizes top-1 accuracy while minimizing null response rate. Outputs the recommended `data/thresholds.json` configuration.

## Design Reference
- See Design Doc §9.3 Threshold Tuning
- See Design Doc §5.3 Confidence Thresholds

## Technical Requirements

### Inputs / Prerequisites
- TASK-100 complete (evaluation harness)

### Implementation Details

1. **Create `scripts/eval/tune.go`** that:
   - Defines a grid of threshold values:
     ```
     SemanticHighThreshold: [0.70, 0.75, 0.78, 0.80, 0.85]
     SemanticMinGap: [0.04, 0.06, 0.08, 0.10, 0.12]
     SemanticAmbiguousThreshold: [0.55, 0.60, 0.65, 0.70]
     RerankerConfidenceFloor: [0.60, 0.65, 0.70, 0.75]
     ```
   - Runs evaluation for each combination (5 × 5 × 4 × 4 = 400 combinations)
   - Records accuracy, null rate, and Tier 3 invocation rate for each
   - Ranks configurations by composite score: `accuracy * 0.7 + (1 - null_rate) * 0.2 + (1 - tier3_rate) * 0.1`
   - Outputs top 10 configurations and recommends the best

2. **Output recommended thresholds** as a new `data/thresholds.json`.

3. **Add Makefile target:**
   ```makefile
   tune-thresholds:
   	go run ./scripts/eval/tune.go -queries scripts/eval/testdata/labeled-queries.json
   ```

### Tech Stack & Dependencies
- `go 1.22+`

## Acceptance Criteria
1. Grid search runs all threshold combinations
2. Each combination is evaluated against the full labeled query set
3. Output includes accuracy, null rate, and Tier 3 rate per configuration
4. Recommended thresholds produce the highest composite score
5. Output writes a valid `data/thresholds.json` file

## Testing Requirements
- **Unit Tests:** Test composite score calculation, grid generation, ranking logic.
- **Integration Tests:** Run with small grid and few test queries for speed.
- **Manual Verification:** Review recommended thresholds against current defaults.

## Files to Create/Modify
- `scripts/eval/tune.go` — (create) Threshold tuning grid search
- `Makefile` — (modify) Add `tune-thresholds` target

## Risks & Edge Cases
- 400 combinations × 200 queries = 80,000 evaluations. In offline mode (no API calls), this completes in minutes. With real embeddings, it requires pre-computed query vectors.
- Overfitting: tuning thresholds to a small test set may not generalize. Recommend splitting labeled queries into train/test sets.

## Notes
- The composite score weights are tunable. The default weighting prioritizes accuracy (70%) while penalizing excessive null responses (20%) and unnecessary Tier 3 calls (10%).
