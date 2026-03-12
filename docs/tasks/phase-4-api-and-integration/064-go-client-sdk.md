# TASK-064: Go Client SDK

## Metadata
- **Phase:** 4
- **Module:** client-sdk
- **Priority:** P2-medium
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-005, TASK-060]
- **Blocks:** None
- **Related:** [TASK-063]

## Objective
Build a Go client SDK in `pkg/client/` that consuming services (like Ada AI) can import to call the Kairos classification API. The SDK handles HTTP client setup, authentication, request/response marshaling, retries, and provides a clean typed interface.

## Design Reference
- See Design Doc §8 Client SDK
- See Design Doc §5 API Contract (request/response types)

## Technical Requirements

### Inputs / Prerequisites
- TASK-005 complete (API types defined as reference)
- TASK-060 complete (classify endpoint to call)

### Implementation Details

1. **Create `pkg/client/client.go`:**

   ```go
   package client

   import (
       "bytes"
       "context"
       "encoding/json"
       "fmt"
       "net/http"
       "time"
   )

   // Client is the Kairos classification API client.
   type Client struct {
       baseURL    string
       apiKey     string
       httpClient *http.Client
   }

   // Option configures the Client.
   type Option func(*Client)

   // WithHTTPClient sets a custom HTTP client.
   func WithHTTPClient(c *http.Client) Option {
       return func(cl *Client) { cl.httpClient = c }
   }

   // WithTimeout sets the HTTP client timeout.
   func WithTimeout(d time.Duration) Option {
       return func(cl *Client) { cl.httpClient.Timeout = d }
   }

   // New creates a new Kairos API client.
   func New(baseURL, apiKey string, opts ...Option) *Client {
       c := &Client{
           baseURL: baseURL,
           apiKey:  apiKey,
           httpClient: &http.Client{
               Timeout: 10 * time.Second,
           },
       }
       for _, opt := range opts {
           opt(c)
       }
       return c
   }

   // ClassifyRequest is the input for classification.
   type ClassifyRequest struct {
       Message             string `json:"message"`
       ConversationContext string `json:"conversation_context,omitempty"`
       SessionID           string `json:"session_id,omitempty"`
   }

   // ClassifyResponse is the classification result.
   type ClassifyResponse struct {
       Product        *ProductResult       `json:"product"`
       Classification ClassificationResult `json:"classification"`
       RequestID      string               `json:"request_id"`
   }

   // ProductResult holds matched product details.
   type ProductResult struct {
       ProductID   string  `json:"product_id"`
       ProductName string  `json:"product_name"`
       Category    string  `json:"category"`
       Confidence  float64 `json:"confidence"`
   }

   // ClassificationResult holds classification metadata.
   type ClassificationResult struct {
       Method        string              `json:"method"`
       Tier          int                 `json:"tier"`
       LatencyMs     int64               `json:"latency_ms"`
       Alternatives  []AlternativeResult `json:"alternatives,omitempty"`
       Reason        string              `json:"reason,omitempty"`
       TopCandidates []CandidateResult   `json:"top_candidates,omitempty"`
   }

   // AlternativeResult is a runner-up match.
   type AlternativeResult struct {
       ProductID  string  `json:"product_id"`
       Confidence float64 `json:"confidence"`
   }

   // CandidateResult is a below-threshold candidate.
   type CandidateResult struct {
       ProductID  string  `json:"product_id"`
       Confidence float64 `json:"confidence"`
   }

   // APIError represents an error returned by the Kairos API.
   type APIError struct {
       StatusCode int
       Code       string `json:"code"`
       Message    string `json:"message"`
       RequestID  string `json:"request_id"`
   }

   func (e *APIError) Error() string {
       return fmt.Sprintf("kairos API error %d (%s): %s [request_id=%s]",
           e.StatusCode, e.Code, e.Message, e.RequestID)
   }

   // Classify sends a classification request to the Kairos API.
   func (c *Client) Classify(ctx context.Context, req ClassifyRequest) (*ClassifyResponse, error) {
       body, err := json.Marshal(req)
       if err != nil {
           return nil, fmt.Errorf("marshaling request: %w", err)
       }

       httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost,
           c.baseURL+"/v1/classify", bytes.NewReader(body))
       if err != nil {
           return nil, fmt.Errorf("creating request: %w", err)
       }

       httpReq.Header.Set("Content-Type", "application/json")
       httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)

       resp, err := c.httpClient.Do(httpReq)
       if err != nil {
           return nil, fmt.Errorf("sending request: %w", err)
       }
       defer resp.Body.Close()

       if resp.StatusCode != http.StatusOK {
           var apiErr struct {
               Error     APIError `json:"error"`
               RequestID string   `json:"request_id"`
           }
           json.NewDecoder(resp.Body).Decode(&apiErr)
           apiErr.Error.StatusCode = resp.StatusCode
           apiErr.Error.RequestID = apiErr.RequestID
           return nil, &apiErr.Error
       }

       var result ClassifyResponse
       if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
           return nil, fmt.Errorf("decoding response: %w", err)
       }

       return &result, nil
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies (standard library HTTP client)

## Acceptance Criteria
1. `client.New("http://localhost:8080", "api-key")` creates a valid client
2. `client.Classify()` sends a properly authenticated request and returns typed response
3. API errors (401, 429, 500) are returned as typed `*APIError` with status code, error code, and message
4. The client respects context cancellation and timeouts
5. Request/response types mirror the API contract exactly
6. The SDK is importable as `github.com/kaseya/kairos/pkg/client`
7. Unit tests use httptest.NewServer to verify HTTP behavior

## Testing Requirements
- **Unit Tests:** Use `httptest.NewServer` to mock the Kairos API. Test successful classify, API errors, timeouts, malformed responses.
- **Integration Tests:** Optional test against running Kairos service.
- **Manual Verification:** None needed

## Files to Create/Modify
- `pkg/client/client.go` — (create) Go client SDK
- `pkg/client/client_test.go` — (create) Unit tests

## Risks & Edge Cases
- Version coupling: if the API contract changes, the SDK must be updated in lockstep. Document this dependency.
- Connection pooling: the default `http.Client` uses connection pooling via `http.DefaultTransport`. This is correct behavior.
- The SDK deliberately does NOT implement retries in v1. Consuming services can wrap with their own retry logic.

## Notes
- The SDK is in `pkg/client/` (not `internal/`) so external services can import it. The types are duplicated from `internal/api/types.go` to avoid importing `internal/`.
