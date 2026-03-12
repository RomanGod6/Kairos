# TASK-047: Tier Interfaces and Test Mocks

## Metadata
- **Phase:** 3
- **Module:** classify
- **Priority:** P1-high
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010, TASK-043]
- **Blocks:** None
- **Related:** [TASK-041, TASK-042, TASK-044, TASK-045, TASK-046]

## Objective
Define clean interfaces for each tier and the Azure AI client, and create mock implementations for testing. This enables unit testing of the pipeline orchestrator and each tier in isolation without real Azure API calls.

## Design Reference
- See Design Doc §4.1 Pipeline Orchestrator (tier interfaces)
- See Design Doc §6 Azure AI Foundry Integration (client interfaces)

## Technical Requirements

### Inputs / Prerequisites
- TASK-010 complete (TierResult types)
- TASK-043 complete (Embedder and Completer interfaces)

### Implementation Details

1. **Create `internal/classify/interfaces.go`:**

   ```go
   package classify

   import "context"

   // KeywordMatcher is the interface for Tier 1 keyword matching.
   type KeywordMatcher interface {
       Match(normalizedInput string) *TierResult
       FuzzyMatch(normalizedInput string) *TierResult
   }

   // SemanticMatcher is the interface for Tier 2 semantic matching.
   type SemanticMatcher interface {
       Match(ctx context.Context, normalizedQuery string) (*TierResult, error)
   }

   // LLMReranker is the interface for Tier 3 LLM reranking.
   type LLMReranker interface {
       Rerank(ctx context.Context, query string, candidates []ScoredCandidate) (*TierResult, error)
   }
   ```

2. **Create `internal/classify/mocks_test.go`** (or a shared `internal/testutil/mocks.go`):

   ```go
   package classify_test

   import "context"

   // MockKeywordMatcher implements KeywordMatcher for testing.
   type MockKeywordMatcher struct {
       MatchResult      *classify.TierResult
       FuzzyMatchResult *classify.TierResult
   }

   func (m *MockKeywordMatcher) Match(input string) *classify.TierResult {
       return m.MatchResult
   }

   func (m *MockKeywordMatcher) FuzzyMatch(input string) *classify.TierResult {
       return m.FuzzyMatchResult
   }

   // MockSemanticMatcher implements SemanticMatcher for testing.
   type MockSemanticMatcher struct {
       Result *classify.TierResult
       Err    error
   }

   func (m *MockSemanticMatcher) Match(ctx context.Context, query string) (*classify.TierResult, error) {
       return m.Result, m.Err
   }

   // MockReranker implements LLMReranker for testing.
   type MockReranker struct {
       Result *classify.TierResult
       Err    error
   }

   func (m *MockReranker) Rerank(ctx context.Context, query string, candidates []classify.ScoredCandidate) (*classify.TierResult, error) {
       return m.Result, m.Err
   }

   // MockEmbedder implements azureai.Embedder for testing.
   type MockEmbedder struct {
       Vectors [][]float64
       Err     error
   }

   func (m *MockEmbedder) Embed(ctx context.Context, texts []string) ([][]float64, error) {
       return m.Vectors, m.Err
   }

   // MockCompleter implements azureai.Completer for testing.
   type MockCompleter struct {
       Response string
       Err      error
   }

   func (m *MockCompleter) Complete(ctx context.Context, req azureai.CompletionRequest) (string, error) {
       return m.Response, m.Err
   }
   ```

3. **Update pipeline to use interfaces** instead of concrete types.

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies

## Acceptance Criteria
1. All tier interfaces are defined with matching method signatures
2. Mock implementations satisfy their respective interfaces (compiler-verified)
3. Pipeline orchestrator accepts interfaces, not concrete types
4. Mocks support configurable return values for all test scenarios
5. Mock tests compile and run without Azure AI credentials

## Testing Requirements
- **Unit Tests:** Verify interface compliance with compile-time assertions: `var _ KeywordMatcher = (*MockKeywordMatcher)(nil)`
- **Integration Tests:** None
- **Manual Verification:** None

## Files to Create/Modify
- `internal/classify/interfaces.go` — (create) Tier interface definitions
- `internal/classify/mocks_test.go` — (create) Mock implementations
- `internal/classify/pipeline.go` — (modify) Accept interfaces instead of concrete types

## Risks & Edge Cases
- Interface changes: if a tier's method signature changes, all mocks and the orchestrator must be updated. Keep interfaces minimal.

## Notes
- Go's implicit interface satisfaction means the concrete tier implementations (in tier1/, tier2/, tier3/ packages) automatically implement these interfaces without import cycles.
