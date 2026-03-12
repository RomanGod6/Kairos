# TASK-060: POST /v1/classify Endpoint

## Metadata
- **Phase:** 4
- **Module:** api
- **Priority:** P0-critical
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003, TASK-005, TASK-006, TASK-046]
- **Blocks:** [TASK-064]
- **Related:** [TASK-063]

## Objective
Implement the `POST /v1/classify` HTTP handler that accepts a user message, runs it through the classification pipeline, and returns the structured JSON response with the matched product, classification metadata, and request ID.

## Design Reference
- See Design Doc §5 API Contract
- See Design Doc §5.1 Classification Request
- See Design Doc §5.2 Classification Response
- See Design Doc §5.3 Null Response

## Technical Requirements

### Inputs / Prerequisites
- TASK-046 complete (Pipeline.Classify)
- TASK-005 complete (API request/response types)
- TASK-006 complete (error response helpers)
- TASK-003 complete (HTTP server with router)

### Implementation Details

1. **Create the classify handler in `internal/api/handler.go`** (extend existing file):

   ```go
   // ClassifyHandler returns an HTTP handler for the classification endpoint.
   func ClassifyHandler(pipeline *classify.Pipeline) http.HandlerFunc {
       return func(w http.ResponseWriter, r *http.Request) {
           // 1. Parse request body
           var req ClassifyRequest
           if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
               WriteBadRequest(w, r, "invalid JSON: "+err.Error())
               return
           }

           // 2. Validate request
           if err := req.Validate(); err != nil {
               WriteValidationError(w, r, err.Error())
               return
           }

           // 3. Run classification pipeline
           result := pipeline.Classify(r.Context(), req.Message)

           // 4. Build response
           reqID := middleware.GetReqID(r.Context())
           resp := ClassifyResponse{
               RequestID: reqID,
               Classification: ClassificationResult{
                   Method:    string(result.Method),
                   Tier:      int(result.Tier),
                   LatencyMs: result.Latency.Milliseconds(),
               },
           }

           // 5. Populate product or null response fields
           if result.IsMatch() {
               resp.Product = &ProductResult{
                   ProductID:   result.ProductID,
                   ProductName: result.ProductName,
                   Category:    result.Category,
                   Confidence:  result.Confidence,
               }
               for _, alt := range result.Alternatives {
                   resp.Classification.Alternatives = append(resp.Classification.Alternatives,
                       AlternativeResult{
                           ProductID:  alt.ProductID,
                           Confidence: alt.Confidence,
                       })
               }
           } else {
               resp.Classification.Reason = result.Reason
               for _, c := range result.TopCandidates {
                   resp.Classification.TopCandidates = append(resp.Classification.TopCandidates,
                       CandidateResult{
                           ProductID:  c.ProductID,
                           Confidence: c.Confidence,
                       })
               }
           }

           // 6. Write response
           WriteJSON(w, http.StatusOK, resp)
       }
   }
   ```

2. **Register the route in `internal/api/routes.go`:**
   ```go
   r.Route("/v1", func(r chi.Router) {
       r.Post("/classify", ClassifyHandler(pipeline))
   })
   ```

3. **Update `NewRouter` to accept the pipeline dependency.**

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/go-chi/chi/v5 v5.1+`

## Acceptance Criteria
1. `POST /v1/classify` with valid body returns HTTP 200 with `ClassifyResponse` JSON
2. Missing `message` field returns HTTP 422 with structured error
3. Invalid JSON body returns HTTP 400 with structured error
4. Null classification (no match) returns `"product": null` with `top_candidates`
5. Successful classification returns `product` with all fields populated
6. Every response includes `request_id` from chi middleware
7. `latency_ms` accurately reflects pipeline processing time
8. The endpoint handles context cancellation (client disconnect) gracefully
9. Unit tests cover all response paths

## Testing Requirements
- **Unit Tests:** Use `httptest.NewRecorder` with mock Pipeline. Test valid request, empty message, oversized message, malformed JSON, successful match, null match.
- **Integration Tests:** Start server with mock pipeline, make HTTP requests, verify response format.
- **Manual Verification:** `curl -X POST http://localhost:8080/v1/classify -H "Content-Type: application/json" -d '{"message":"vsa agent offline"}'`

## Files to Create/Modify
- `internal/api/handler.go` — (modify) Add ClassifyHandler
- `internal/api/handler_test.go` — (modify) Add classify handler tests
- `internal/api/routes.go` — (modify) Register classify route with pipeline dependency

## Risks & Edge Cases
- Request body size: limit to 64KB via `http.MaxBytesReader` to prevent memory abuse.
- Concurrent requests: the pipeline is stateless and safe for concurrent use. No additional synchronization needed in the handler.
- JSON decoder may accept partial JSON — `Decode` reads the first complete JSON value. This is acceptable.

## Notes
- Authentication middleware (TASK-061) and rate limiting (TASK-062) will wrap this endpoint. For initial testing, the endpoint is unauthenticated.
