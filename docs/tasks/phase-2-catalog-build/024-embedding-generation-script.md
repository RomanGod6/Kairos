# TASK-024: Embedding Generation Script

## Metadata
- **Phase:** 2
- **Module:** scripts
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-021, TASK-011]
- **Blocks:** [TASK-042, TASK-043]
- **Related:** [TASK-023]

## Objective
Build a script that reads the finalized `data/catalog.json`, sends all embedding anchor texts to Azure AI Foundry's embedding endpoint, and writes the resulting vectors to `data/embeddings.json`. This pre-computation avoids runtime embedding of product descriptions and enables fast cosine similarity at request time.

## Design Reference
- See Design Doc §3.2 Data Pipeline — Embed phase
- See Design Doc §4.3 Tier 2: Semantic Embedding Match (pre-computed vectors)

## Technical Requirements

### Inputs / Prerequisites
- TASK-021 complete (finalized `data/catalog.json` exists)
- Azure AI Foundry credentials with access to embedding model deployment
- TASK-011 complete (`EmbeddingCache` type defined)

### Implementation Details

1. **Create `scripts/embed-catalog/main.go`:**

   ```go
   package main

   import (
       "context"
       "encoding/json"
       "flag"
       "fmt"
       "log"
       "os"
       "time"

       "github.com/kaseya/kairos/internal/catalog"
   )

   func main() {
       catalogPath := flag.String("catalog", "data/catalog.json", "Path to catalog JSON")
       outputPath := flag.String("output", "data/embeddings.json", "Output embeddings path")
       endpoint := flag.String("endpoint", os.Getenv("AZURE_AI_FOUNDRY_ENDPOINT"), "Azure AI endpoint")
       apiKey := flag.String("api-key", os.Getenv("AZURE_AI_FOUNDRY_API_KEY"), "Azure AI API key")
       deployment := flag.String("deployment", "text-embedding-3-small", "Embedding model deployment")
       dimensions := flag.Int("dimensions", 1536, "Embedding dimensions")
       batchSize := flag.Int("batch-size", 20, "Texts per embedding API call")
       flag.Parse()

       // Load catalog
       data, err := os.ReadFile(*catalogPath)
       if err != nil {
           log.Fatalf("failed to read catalog: %v", err)
       }
       var cat catalog.Catalog
       if err := json.Unmarshal(data, &cat); err != nil {
           log.Fatalf("failed to parse catalog: %v", err)
       }

       // Collect all anchor texts with product association
       type anchorRef struct {
           ProductID string
           Text      string
       }
       var allAnchors []anchorRef
       for _, p := range cat.Products {
           for _, anchor := range p.EmbeddingAnchors {
               allAnchors = append(allAnchors, anchorRef{ProductID: p.ProductID, Text: anchor})
           }
       }
       log.Printf("generating embeddings for %d anchors across %d products", len(allAnchors), len(cat.Products))

       // Initialize Azure AI Foundry embedding client
       // (Use the same client abstraction as internal/azureai/ or direct SDK call)
       client := newEmbeddingClient(*endpoint, *apiKey, *deployment)

       // Batch embed all anchors
       results := make(map[string][]catalog.AnchorEmbedding)
       for i := 0; i < len(allAnchors); i += *batchSize {
           end := i + *batchSize
           if end > len(allAnchors) {
               end = len(allAnchors)
           }
           batch := allAnchors[i:end]

           texts := make([]string, len(batch))
           for j, a := range batch {
               texts[j] = a.Text
           }

           ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
           vectors, err := client.Embed(ctx, texts)
           cancel()
           if err != nil {
               log.Fatalf("embedding batch %d-%d failed: %v", i, end, err)
           }

           for j, a := range batch {
               results[a.ProductID] = append(results[a.ProductID], catalog.AnchorEmbedding{
                   Text:   a.Text,
                   Vector: vectors[j],
               })
           }

           log.Printf("embedded batch %d-%d (%d/%d)", i, end, end, len(allAnchors))
           time.Sleep(500 * time.Millisecond) // Rate limit courtesy
       }

       // Build output
       cache := catalog.EmbeddingCache{
           ModelID:    *deployment,
           Dimensions: *dimensions,
       }
       for _, p := range cat.Products {
           cache.Products = append(cache.Products, catalog.ProductEmbeddings{
               ProductID: p.ProductID,
               Anchors:   results[p.ProductID],
           })
       }

       // Write output
       out, err := json.MarshalIndent(cache, "", "  ")
       if err != nil {
           log.Fatalf("failed to marshal embeddings: %v", err)
       }
       if err := os.WriteFile(*outputPath, out, 0644); err != nil {
           log.Fatalf("failed to write embeddings: %v", err)
       }

       log.Printf("wrote embeddings for %d products to %s", len(cache.Products), *outputPath)
   }
   ```

2. **Implement batch embedding client** that calls Azure AI Foundry's embedding API with proper authentication and error handling.

3. **Add Makefile target:**
   ```makefile
   embed-catalog:
   	go run ./scripts/embed-catalog/ \
   		-catalog data/catalog.json \
   		-output data/embeddings.json
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/Azure/azure-sdk-for-go/sdk/ai/azopenai` — latest stable
- `github.com/Azure/azure-sdk-for-go/sdk/azcore` — latest stable

## Acceptance Criteria
1. Running the script produces `data/embeddings.json` with vectors for all catalog products
2. Every embedding anchor in the catalog has a corresponding vector in the output
3. All vectors have exactly the configured number of dimensions (default: 1536)
4. The output file is valid JSON parseable by `Store.LoadEmbeddings()`
5. Batch processing correctly associates vectors with their source products
6. The script handles Azure AI rate limits gracefully with delays between batches
7. The output includes the model ID and dimensions metadata

## Testing Requirements
- **Unit Tests:** Test batch grouping logic, output file assembly, vector-to-product association.
- **Integration Tests:** Run with a real Azure AI Foundry endpoint and 2-3 test anchors.
- **Manual Verification:** Verify `data/embeddings.json` has correct structure and vector dimensions.

## Files to Create/Modify
- `scripts/embed-catalog/main.go` — (create) Embedding generation script
- `Makefile` — (modify) Add `embed-catalog` target

## Risks & Edge Cases
- Azure AI rate limits: the 500ms delay between batches should suffice for standard tier. If hitting limits, increase the delay or reduce batch size.
- Large catalog: 44 products × 5 anchors = 220 texts. At batch size 20, that's 11 API calls — takes ~10 seconds. Manageable.
- Model version drift: if the embedding model is updated on Azure, all embeddings must be regenerated. Document this in the runbook.
- Network failures: the script should fail fast (not silently produce partial output). Failed batches cause a fatal error.

## Notes
- This script runs once after catalog creation and whenever the catalog changes or the embedding model is updated.
- The embedding vectors are committed to the repo (`data/embeddings.json`) so the service can start without Azure AI access at startup.
