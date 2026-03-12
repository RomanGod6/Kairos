# TASK-005: API Request and Response Type Definitions

## Metadata
- **Phase:** 1
- **Module:** api
- **Priority:** P1-high
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001]
- **Blocks:** [TASK-060, TASK-063, TASK-064]
- **Related:** [TASK-046]

## Objective
Define all request and response struct types for the Kairos API, establishing the contract that HTTP handlers, the classification pipeline, and the Go client SDK all share. These types are the canonical source of truth for JSON serialization.

## Design Reference
- See Design Doc §5 API Contract (full request/response schemas)
- See Design Doc §5.1 Classification Request
- See Design Doc §5.2 Classification Response
- See Design Doc §5.3 Null Response

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (Go module exists)

### Implementation Details

1. **Create `internal/api/types.go`:**

   ```go
   package api

   // ClassifyRequest is the JSON body for POST /v1/classify.
   type ClassifyRequest struct {
       Message             string `json:"message"`
       ConversationContext string `json:"conversation_context,omitempty"`
       SessionID           string `json:"session_id,omitempty"`
   }

   // ClassifyResponse is the JSON response for POST /v1/classify.
   type ClassifyResponse struct {
       Product        *ProductResult        `json:"product"`
       Classification ClassificationResult  `json:"classification"`
       RequestID      string                `json:"request_id"`
   }

   // ProductResult contains the matched product details.
   // Nil when no product matches above the confidence threshold.
   type ProductResult struct {
       ProductID   string  `json:"product_id"`
       ProductName string  `json:"product_name"`
       Category    string  `json:"category"`
       Confidence  float64 `json:"confidence"`
   }

   // ClassificationResult contains metadata about how the classification was performed.
   type ClassificationResult struct {
       Method       string              `json:"method"`
       Tier         int                 `json:"tier"`
       LatencyMs    int64               `json:"latency_ms"`
       Alternatives []AlternativeResult `json:"alternatives,omitempty"`
       Reason       string              `json:"reason,omitempty"`
       TopCandidates []CandidateResult  `json:"top_candidates,omitempty"`
   }

   // AlternativeResult represents a runner-up product match.
   type AlternativeResult struct {
       ProductID  string  `json:"product_id"`
       Confidence float64 `json:"confidence"`
   }

   // CandidateResult is used in null responses to show what was closest.
   type CandidateResult struct {
       ProductID  string  `json:"product_id"`
       Confidence float64 `json:"confidence"`
   }

   // ErrorResponse is the standard error JSON envelope.
   type ErrorResponse struct {
       Error     ErrorDetail `json:"error"`
       RequestID string      `json:"request_id"`
   }

   // ErrorDetail contains error specifics.
   type ErrorDetail struct {
       Code    string `json:"code"`
       Message string `json:"message"`
   }
   ```

2. **Add validation method on `ClassifyRequest`:**

   ```go
   import "fmt"

   const maxMessageLength = 2000

   // Validate checks that the classify request is well-formed.
   func (r *ClassifyRequest) Validate() error {
       if r.Message == "" {
           return fmt.Errorf("message is required")
       }
       if len(r.Message) > maxMessageLength {
           return fmt.Errorf("message exceeds maximum length of %d characters", maxMessageLength)
       }
       return nil
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies (standard library only)

## Acceptance Criteria
1. All types serialize to JSON matching the exact API contract (field names, omitempty behavior)
2. `ClassifyResponse` with `Product: nil` produces `"product": null` in JSON
3. `ClassifyRequest.Validate()` rejects empty messages and messages over 2000 characters
4. `ErrorResponse` produces consistent error JSON format
5. All JSON tags are lowercase snake_case
6. Unit tests verify JSON serialization round-trips for all types

## Testing Requirements
- **Unit Tests:** Marshal/unmarshal each type to/from JSON and verify field names and values. Test nil product serialization. Test `Validate()` with empty, valid, and oversized messages.
- **Integration Tests:** None needed — these are data types
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/api/types.go` — (create) All request/response type definitions
- `internal/api/types_test.go` — (create) Serialization and validation tests

## Risks & Edge Cases
- JSON `omitempty` on slice fields: empty slice `[]` vs nil slice `null` — decide which the API contract requires and test accordingly. Use `omitempty` on `Alternatives` (omit when empty) but NOT on `TopCandidates` in null responses (should always appear).
- Ensure `float64` confidence values don't produce unnecessary precision in JSON output (e.g., `0.920000000001`). Standard `encoding/json` handles this correctly for most cases.

## Notes
- These types will be duplicated in `pkg/client/` for the Go SDK in TASK-064 to avoid importing `internal/`. The SDK types should mirror these exactly.
- The `maxMessageLength` constant of 2000 is aligned with typical user chat message sizes. This can be made configurable later if needed.
