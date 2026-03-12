# TASK-102: Ada Feedback Loop Webhook

## Metadata
- **Phase:** 6
- **Module:** api
- **Priority:** P2-medium
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-060]
- **Blocks:** None
- **Related:** [TASK-100]

## Objective
Implement a `POST /v1/feedback` endpoint that Ada AI (or operators) can call to report misclassification signals. The feedback is logged as structured JSON for offline analysis and added to a feedback buffer that can be exported as new labeled queries for the evaluation harness.

## Design Reference
- See Design Doc §9.4 Feedback Loop
- See Design Doc §5.6 Feedback Endpoint

## Technical Requirements

### Inputs / Prerequisites
- TASK-060 complete (API framework exists)

### Implementation Details

1. **Define feedback request type:**

   ```go
   type FeedbackRequest struct {
       RequestID        string `json:"request_id"`
       PredictedProduct string `json:"predicted_product_id"`
       CorrectProduct   string `json:"correct_product_id,omitempty"`
       FeedbackType     string `json:"feedback_type"` // "wrong", "correct", "null_should_match"
       UserMessage      string `json:"user_message,omitempty"`
       Notes            string `json:"notes,omitempty"`
   }
   ```

2. **Create feedback handler:**
   - Validate the feedback request
   - Log the feedback at INFO level with all fields (structured JSON)
   - Append to an in-memory feedback buffer (ring buffer, max 10,000 entries)
   - Return acknowledgment response

3. **Create `GET /admin/feedback/export`** endpoint that exports buffered feedback as a JSON file suitable for use as labeled queries in the evaluation harness.

4. **Feedback types:**
   - `wrong` — Product was classified but the wrong one was returned
   - `correct` — Product was classified correctly (positive signal)
   - `null_should_match` — No product matched but one should have

### Tech Stack & Dependencies
- `go 1.22+`

## Acceptance Criteria
1. `POST /v1/feedback` accepts and validates feedback data
2. Feedback is logged as structured JSON with request_id, predicted, correct, and type
3. In-memory buffer holds up to 10,000 feedback entries
4. `GET /admin/feedback/export` returns buffered feedback as JSON array
5. Exported feedback format is compatible with the eval harness labeled query format
6. Endpoint requires authentication

## Testing Requirements
- **Unit Tests:** Test feedback validation, buffer management (ring buffer overflow), export format.
- **Integration Tests:** Submit feedback, export, verify format.
- **Manual Verification:** Submit feedback via curl, verify structured log output.

## Files to Create/Modify
- `internal/api/handler.go` — (modify) Add FeedbackHandler and ExportFeedbackHandler
- `internal/api/types.go` — (modify) Add FeedbackRequest type
- `internal/api/routes.go` — (modify) Register feedback endpoints

## Risks & Edge Cases
- Feedback data is not persisted to disk — it's lost on restart. For production, consider writing to a file or external store. The in-memory buffer is sufficient for v1.
- Malicious feedback could poison the evaluation dataset. Admin-only export and human review mitigate this.

## Notes
- The feedback loop is the mechanism for continuous improvement. Over time, feedback accumulates into a growing labeled dataset that makes the eval harness increasingly representative.
