# TASK-025: Catalog Validation CLI Tool

## Metadata
- **Phase:** 2
- **Module:** scripts
- **Priority:** P2-medium
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-011, TASK-022]
- **Blocks:** None
- **Related:** [TASK-021, TASK-023, TASK-024]

## Objective
Create a standalone CLI tool that validates `catalog.json` and `embeddings.json` for schema correctness, cross-referential integrity (every catalog product has embeddings and vice versa), and data quality (minimum alias count, anchor count, vector dimensions). Used in CI and before deployments.

## Design Reference
- See Design Doc §3.4 Catalog Loading — validation rules
- See Design Doc §7.1 CI/CD Pipeline — pre-deployment checks

## Technical Requirements

### Inputs / Prerequisites
- TASK-022 complete (catalog Store with validation)
- TASK-011 complete (types with Validate methods)

### Implementation Details

1. **Create `scripts/validate-catalog/main.go`:**
   - Load `catalog.json` via `Store.LoadCatalog()`
   - Load `embeddings.json` via `Store.LoadEmbeddings()`
   - Run schema validation (existing `Validate()` methods)
   - Check cross-references: every product has embeddings, every embedding references a valid product
   - Check data quality minimums:
     - Each product has ≥ 3 aliases
     - Each product has ≥ 5 signal phrases
     - Each product has ≥ 2 embedding anchors
     - All embedding vectors have the correct dimensionality
   - Print a report with pass/fail per check and summary
   - Exit 0 if all checks pass, exit 1 if any fail

2. **Add Makefile target:**
   ```makefile
   validate-catalog:
   	go run ./scripts/validate-catalog/
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies

## Acceptance Criteria
1. The tool exits 0 for valid catalog + embeddings pair
2. The tool exits 1 and prints specific failures for invalid data
3. Missing embeddings for a catalog product are flagged
4. Orphaned embeddings (no matching product) are flagged
5. Dimension mismatches in embedding vectors are flagged
6. Below-minimum alias/signal/anchor counts are flagged per product
7. The tool can be run in CI as a pre-deployment gate

## Testing Requirements
- **Unit Tests:** Test validation logic with intentionally broken catalog/embedding combinations.
- **Integration Tests:** None
- **Manual Verification:** Run `make validate-catalog` against sample data from TASK-023.

## Files to Create/Modify
- `scripts/validate-catalog/main.go` — (create) Validation CLI tool
- `Makefile` — (modify) Add `validate-catalog` target

## Risks & Edge Cases
- Partial embedding files (some products missing) should produce warnings, not hard failures, during development. Use `--strict` flag for CI enforcement.

## Notes
- This tool is lightweight and fast — it only reads and validates JSON files. No external API calls.
