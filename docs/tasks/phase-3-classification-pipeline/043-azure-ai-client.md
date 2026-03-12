# TASK-043: Azure AI Foundry Client — Embeddings and Completions

## Metadata
- **Phase:** 3
- **Module:** azureai
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-002, TASK-010]
- **Blocks:** [TASK-044, TASK-045, TASK-046]
- **Related:** [TASK-024]

## Objective
Build the Azure AI Foundry client package (`internal/azureai/`) that wraps the Azure SDK to provide two clean interfaces: `Embedder` for Tier 2 embedding generation and `Completer` for Tier 3 LLM reranker calls. This abstraction isolates all external API communication and makes it trivial to swap models or mock in tests.

## Design Reference
- See Design Doc §6 Azure AI Foundry Integration
- See Design Doc §6.1 Configuration (endpoint, API key, deployment names)
- See Design Doc §6.2 Embeddings API
- See Design Doc §6.3 Chat Completions API

## Technical Requirements

### Inputs / Prerequisites
- TASK-002 complete (AzureAIConfig available)

### Implementation Details

1. **Create `internal/azureai/client.go`:**

   ```go
   package azureai

   import (
       "context"

       "github.com/kaseya/kairos/internal/config"
   )

   // Embedder generates embedding vectors for text inputs.
   type Embedder interface {
       // Embed generates embedding vectors for the given texts.
       // Returns one vector per input text.
       Embed(ctx context.Context, texts []string) ([][]float64, error)
   }

   // Completer performs chat completion requests (used by the reranker).
   type Completer interface {
       // Complete sends a chat completion request and returns the response text.
       Complete(ctx context.Context, req CompletionRequest) (string, error)
   }

   // CompletionRequest holds parameters for a chat completion call.
   type CompletionRequest struct {
       SystemPrompt string
       UserPrompt   string
       MaxTokens    int
       Temperature  float64
   }

   // Client wraps the Azure AI Foundry SDK, implementing both Embedder and Completer.
   type Client struct {
       cfg config.AzureAIConfig
       // Internal Azure SDK client references will be stored here
   }

   // NewClient creates a new Azure AI Foundry client.
   func NewClient(cfg config.AzureAIConfig) (*Client, error) {
       // Initialize Azure SDK client with API key authentication
       // Validate endpoint and credentials
       return &Client{cfg: cfg}, nil
   }
   ```

2. **Create `internal/azureai/embeddings.go`:**

   ```go
   package azureai

   import (
       "context"
       "fmt"
       "time"

       "github.com/Azure/azure-sdk-for-go/sdk/ai/azopenai"
       "github.com/Azure/azure-sdk-for-go/sdk/azcore"
   )

   // Embed implements the Embedder interface.
   func (c *Client) Embed(ctx context.Context, texts []string) ([][]float64, error) {
       body := azopenai.EmbeddingsOptions{
           Input:          texts,
           DeploymentName: &c.cfg.EmbeddingDeployment,
       }

       resp, err := c.embeddingClient.GetEmbeddings(ctx, body, nil)
       if err != nil {
           return nil, fmt.Errorf("azure embedding API error: %w", err)
       }

       vectors := make([][]float64, len(resp.Data))
       for i, item := range resp.Data {
           vec := make([]float64, len(item.Embedding))
           for j, v := range item.Embedding {
               vec[j] = float64(v)
           }
           vectors[i] = vec
       }

       return vectors, nil
   }
   ```

3. **Create `internal/azureai/completions.go`:**

   ```go
   package azureai

   import (
       "context"
       "fmt"

       "github.com/Azure/azure-sdk-for-go/sdk/ai/azopenai"
   )

   // Complete implements the Completer interface.
   func (c *Client) Complete(ctx context.Context, req CompletionRequest) (string, error) {
       maxTokens := int32(req.MaxTokens)
       temp := float32(req.Temperature)

       body := azopenai.ChatCompletionsOptions{
           DeploymentName: &c.cfg.RerankerDeployment,
           Messages: []azopenai.ChatRequestMessageClassification{
               &azopenai.ChatRequestSystemMessage{
                   Content: azopenai.NewChatRequestSystemMessageContent(req.SystemPrompt),
               },
               &azopenai.ChatRequestUserMessage{
                   Content: azopenai.NewChatRequestUserMessageContent(req.UserPrompt),
               },
           },
           MaxTokens:   &maxTokens,
           Temperature: &temp,
       }

       resp, err := c.completionClient.GetChatCompletions(ctx, body, nil)
       if err != nil {
           return "", fmt.Errorf("azure completion API error: %w", err)
       }

       if len(resp.Choices) == 0 {
           return "", fmt.Errorf("azure completion returned no choices")
       }

       content := resp.Choices[0].Message.Content
       if content == nil {
           return "", fmt.Errorf("azure completion returned nil content")
       }

       return *content, nil
   }
   ```

4. **Error handling and timeouts:**
   - Each `Embed()` call should respect the context deadline
   - Each `Complete()` call should have a maximum timeout of `RerankerTimeout` from config
   - On HTTP 429 (rate limited), return a typed error `ErrRateLimited` that the pipeline can handle
   - On HTTP 5xx, return a typed error `ErrServiceUnavailable`

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/Azure/azure-sdk-for-go/sdk/ai/azopenai` — latest stable (verify as of March 2026)
- `github.com/Azure/azure-sdk-for-go/sdk/azcore` — latest stable

## Acceptance Criteria
1. `Embed()` sends texts to Azure AI Foundry and returns float64 vectors of correct dimensions
2. `Complete()` sends a system+user prompt and returns the response text
3. Both methods respect context cancellation and timeouts
4. Azure API errors are wrapped with context (embedding vs completion, HTTP status)
5. `ErrRateLimited` and `ErrServiceUnavailable` error types are defined and returned appropriately
6. `Embedder` and `Completer` interfaces allow easy mocking in tests
7. Unit tests use mock HTTP server to test client behavior without real Azure calls
8. The client validates configuration on creation (fails fast for bad endpoint/missing key)

## Testing Requirements
- **Unit Tests:** Use `httptest.NewServer` to mock Azure AI Foundry responses. Test success paths, error responses (429, 500, timeout), malformed responses. Test interface compliance.
- **Integration Tests:** Optional test with real Azure AI Foundry (gated by env var flag).
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/azureai/client.go` — (create) Client initialization and interfaces
- `internal/azureai/embeddings.go` — (create) Embedding API implementation
- `internal/azureai/completions.go` — (create) Chat completions API implementation
- `internal/azureai/errors.go` — (create) Typed error definitions
- `internal/azureai/client_test.go` — (create) Unit tests with mock server
- `go.mod` — (modify) Add Azure SDK dependencies

## Risks & Edge Cases
- Azure SDK API surface may change between versions. Pin to a specific version in `go.mod`.
- Embedding vectors from the SDK may be `float32`, not `float64`. The conversion is in `Embed()` — verify the SDK response type.
- Azure AI Foundry endpoint URL format must include the resource name. Validate URL format in `NewClient`.
- Token-level billing: each embedding and completion call has a cost. The client does not enforce budgets — that's an operational concern.

## Notes
- The `Embedder` and `Completer` interfaces are the seam for testing. All tier-level code depends on interfaces, never on the concrete `Client` type.
- Consider adding a `Close()` method if the Azure SDK client holds connection pools.
