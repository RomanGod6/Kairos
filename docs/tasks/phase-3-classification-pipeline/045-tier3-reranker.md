# TASK-045: Tier 3 — LLM Reranker

## Metadata
- **Phase:** 3
- **Module:** tier3
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010, TASK-011, TASK-022, TASK-043]
- **Blocks:** [TASK-046]
- **Related:** [TASK-044]

## Objective
Implement the Tier 3 LLM reranker that is invoked when Tier 2 produces ambiguous results (top candidates too close in score). The reranker sends a structured prompt with the user query and top candidates to an LLM via Azure AI Foundry, asking it to select the single best product match. It operates with temperature 0, max 10 tokens, and a 2-second timeout.

## Design Reference
- See Design Doc §4.4 Tier 3: LLM Reranker
- See Design Doc §4.4.1 Reranker Prompt Template
- See Design Doc §4.4.2 Fallback Behavior
- See Design Doc §5.3 Confidence Thresholds (RERANKER_CONFIDENCE_FLOOR = 0.70)

## Technical Requirements

### Inputs / Prerequisites
- TASK-043 complete (Azure AI Foundry Completer interface)
- TASK-022 complete (catalog Store for product details and disambiguation hints)
- TASK-010 complete (TierResult, ScoredCandidate types)

### Implementation Details

1. **Create `internal/tier3/prompt.go`:**

   ```go
   package tier3

   import (
       "fmt"
       "strings"

       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
   )

   const systemPrompt = `You are a product classifier for Kaseya's IT management product suite.
   Given a user message and a list of candidate products, select the single best matching product.
   Respond with ONLY the product_id of the best match. Nothing else.`

   // BuildUserPrompt constructs the reranker prompt with the query and candidates.
   func BuildUserPrompt(query string, candidates []classify.ScoredCandidate, store *catalog.Store) string {
       var sb strings.Builder

       sb.WriteString(fmt.Sprintf("User message: %q\n\n", query))
       sb.WriteString("Candidate products:\n")

       for i, c := range candidates {
           product := store.GetProductByID(c.ProductID)
           if product == nil {
               continue
           }

           sb.WriteString(fmt.Sprintf("\n%d. %s (product_id: %s)\n", i+1, c.ProductName, c.ProductID))
           sb.WriteString(fmt.Sprintf("   Category: %s\n", product.Category))
           sb.WriteString(fmt.Sprintf("   Description: %s\n", product.Description))
           if product.DisambiguationHints != "" {
               sb.WriteString(fmt.Sprintf("   Disambiguation: %s\n", product.DisambiguationHints))
           }
           sb.WriteString(fmt.Sprintf("   Similarity score: %.3f\n", c.Score))
       }

       sb.WriteString("\nWhich product_id best matches the user message? Respond with only the product_id.")

       return sb.String()
   }
   ```

2. **Create `internal/tier3/reranker.go`:**

   ```go
   package tier3

   import (
       "context"
       "fmt"
       "strings"
       "time"

       "github.com/kaseya/kairos/internal/azureai"
       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
       "github.com/kaseya/kairos/internal/config"
       "github.com/rs/zerolog/log"
   )

   const maxCandidatesForReranker = 5

   // Reranker performs Tier 3 LLM-based reranking of ambiguous results.
   type Reranker struct {
       completer  azureai.Completer
       store      *catalog.Store
       thresholds config.ThresholdConfig
       timeout    time.Duration
       maxTokens  int
   }

   // NewReranker creates a Tier 3 reranker.
   func NewReranker(completer azureai.Completer, store *catalog.Store, cfg config.AzureAIConfig, thresholds config.ThresholdConfig) *Reranker {
       return &Reranker{
           completer:  completer,
           store:      store,
           thresholds: thresholds,
           timeout:    cfg.RerankerTimeout,
           maxTokens:  cfg.RerankerMaxTokens,
       }
   }

   // Rerank takes ambiguous Tier 2 candidates and asks the LLM to select the best match.
   func (r *Reranker) Rerank(ctx context.Context, query string, candidates []classify.ScoredCandidate) (*classify.TierResult, error) {
       // Limit candidates sent to LLM
       if len(candidates) > maxCandidatesForReranker {
           candidates = candidates[:maxCandidatesForReranker]
       }

       // Build prompt
       userPrompt := BuildUserPrompt(query, candidates, r.store)

       // Apply reranker-specific timeout
       ctx, cancel := context.WithTimeout(ctx, r.timeout)
       defer cancel()

       // Call LLM
       response, err := r.completer.Complete(ctx, azureai.CompletionRequest{
           SystemPrompt: systemPrompt,
           UserPrompt:   userPrompt,
           MaxTokens:    r.maxTokens,
           Temperature:  0,
       })
       if err != nil {
           log.Warn().Err(err).Msg("reranker LLM call failed, falling back to Tier 2 top match")
           return r.fallbackToTier2Top(candidates), nil
       }

       // Parse response — expect a single product_id
       selectedID := strings.TrimSpace(response)
       selectedID = strings.Trim(selectedID, "\"'`")

       // Validate the selected product exists in candidates
       for _, c := range candidates {
           if c.ProductID == selectedID {
               confidence := c.Score
               if confidence < r.thresholds.RerankerConfidenceFloor {
                   confidence = r.thresholds.RerankerConfidenceFloor
               }

               return &classify.TierResult{
                   Matched:    true,
                   ProductID:  c.ProductID,
                   Confidence: confidence,
                   Method:     classify.MethodReranker,
                   Candidates: candidates,
               }, nil
           }
       }

       // LLM returned an invalid product_id — fallback
       log.Warn().Str("llm_response", selectedID).Msg("reranker returned invalid product_id, falling back")
       return r.fallbackToTier2Top(candidates), nil
   }

   // fallbackToTier2Top returns the Tier 2 top candidate as a degraded result.
   func (r *Reranker) fallbackToTier2Top(candidates []classify.ScoredCandidate) *classify.TierResult {
       if len(candidates) == 0 {
           return &classify.TierResult{
               Matched: false,
               Method:  classify.MethodReranker,
           }
       }

       top := candidates[0]
       // Apply a small confidence penalty for degraded path
       confidence := top.Score * 0.95

       return &classify.TierResult{
           Matched:    confidence >= r.thresholds.RerankerConfidenceFloor,
           ProductID:  top.ProductID,
           Confidence: confidence,
           Method:     classify.MethodReranker,
           Candidates: candidates,
       }
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/rs/zerolog v1.33+` (for logging fallback paths)

## Acceptance Criteria
1. Reranker sends a well-structured prompt with query, candidates, descriptions, and disambiguation hints
2. Valid LLM response (returns a product_id from candidates) → confident match with score ≥ 0.70
3. LLM timeout (> 2s) → fallback to Tier 2 top candidate with 5% confidence penalty
4. LLM error (API failure) → fallback to Tier 2 top candidate with 5% confidence penalty
5. LLM returns invalid product_id → fallback with warning log
6. Max 5 candidates are sent to the reranker (limit prompt size)
7. Temperature is always 0, max tokens is always 10
8. Fallback results are still gated by `RERANKER_CONFIDENCE_FLOOR` (0.70)
9. Unit test coverage ≥ 90% (using mock Completer)

## Testing Requirements
- **Unit Tests:** Test with mock Completer returning valid product_id, invalid product_id, error, and timeout. Test prompt generation with various candidate sets. Test fallback path confidence penalty.
- **Integration Tests:** Optional test with real Azure AI Foundry.
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/tier3/prompt.go` — (create) Prompt template builder
- `internal/tier3/reranker.go` — (create) Reranker logic with fallback
- `internal/tier3/prompt_test.go` — (create) Prompt construction tests
- `internal/tier3/reranker_test.go` — (create) Reranker logic tests

## Risks & Edge Cases
- LLM may return the product_id with extra whitespace, quotes, or markdown formatting. The parsing step strips these.
- LLM may hallucinate a product_id that isn't in the candidate list. The validation step catches this and falls back.
- Very short queries (e.g., "backup") may produce poor reranker results since there's little context. The reranker still helps by considering product descriptions and disambiguation hints.
- The 2-second timeout is tight but appropriate for a 10-token response. If the Azure endpoint is slow, consider increasing to 3s.

## Notes
- The reranker fires on only ~10-15% of requests (ambiguous Tier 2 results). This keeps LLM costs low.
- The system prompt is intentionally minimal to keep token count low and response time fast.
- The fallback path ensures the service always returns a result even when the LLM is unavailable — this is critical for reliability.
