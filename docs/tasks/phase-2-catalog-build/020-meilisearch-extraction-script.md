# TASK-020: Meilisearch Product Data Extraction Script

## Metadata
- **Phase:** 2
- **Module:** scripts
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001, TASK-009, TASK-011]
- **Blocks:** [TASK-021]
- **Related:** None

## Objective
Build the extraction script (`scripts/extract-catalog/extract.go`) that queries the existing Meilisearch instance to pull all product documentation, deduplicates multi-page crawl results, and produces a normalized intermediate JSON file with one entry per product. This is step 1 of the catalog build pipeline.

## Design Reference
- See Design Doc §3.2 Data Pipeline — Extract phase
- See Design Doc §3.3 Meilisearch Source Data

## Technical Requirements

### Inputs / Prerequisites
- Meilisearch instance running (via docker-compose from TASK-009 or existing infrastructure)
- Meilisearch contains crawled documentation for all 44 Kaseya products
- TASK-011 complete (Product type defined for output target)

### Implementation Details

1. **Create `scripts/extract-catalog/extract.go`** as a standalone CLI tool:

   ```go
   package main

   import (
       "context"
       "encoding/json"
       "flag"
       "fmt"
       "log"
       "os"
       "strings"

       "github.com/meilisearch/meilisearch-go"
   )

   // RawDocument represents a single crawled page from Meilisearch.
   type RawDocument struct {
       ID          string `json:"id"`
       Title       string `json:"title"`
       Content     string `json:"content"`
       URL         string `json:"url"`
       ProductSlug string `json:"product_slug"`
       CrawledAt   string `json:"crawled_at"`
   }

   // ExtractedProduct is the intermediate output per product.
   type ExtractedProduct struct {
       ProductSlug  string   `json:"product_slug"`
       ProductName  string   `json:"product_name"`
       URLs         []string `json:"urls"`
       CombinedText string   `json:"combined_text"`
       PageCount    int      `json:"page_count"`
   }

   func main() {
       meiliHost := flag.String("host", "http://localhost:7700", "Meilisearch host")
       meiliKey := flag.String("key", "dev-master-key", "Meilisearch API key")
       indexName := flag.String("index", "products", "Meilisearch index name")
       outputPath := flag.String("output", "data/raw-extract.json", "Output file path")
       flag.Parse()

       client := meilisearch.New(*meiliHost, meilisearch.WithAPIKey(*meiliKey))

       // Verify connectivity
       if _, err := client.Health(); err != nil {
           log.Fatalf("cannot reach Meilisearch at %s: %v", *meiliHost, err)
       }

       index := client.Index(*indexName)

       // Paginated extraction — fetch all documents
       var allDocs []RawDocument
       offset := int64(0)
       limit := int64(100)

       for {
           resp, err := index.GetDocuments(&meilisearch.DocumentsQuery{
               Offset: offset,
               Limit:  limit,
           })
           if err != nil {
               log.Fatalf("failed to fetch documents at offset %d: %v", offset, err)
           }

           // Decode results into RawDocument slice
           // (implementation depends on Meilisearch Go SDK version)
           batch := decodeDocuments(resp.Results)
           allDocs = append(allDocs, batch...)

           if int64(len(batch)) < limit {
               break
           }
           offset += limit
       }

       log.Printf("extracted %d raw documents", len(allDocs))

       // Group by product slug and merge
       grouped := groupByProduct(allDocs)
       log.Printf("grouped into %d unique products", len(grouped))

       // Write output
       out, err := json.MarshalIndent(grouped, "", "  ")
       if err != nil {
           log.Fatalf("failed to marshal output: %v", err)
       }
       if err := os.WriteFile(*outputPath, out, 0644); err != nil {
           log.Fatalf("failed to write output: %v", err)
       }

       log.Printf("wrote %d products to %s", len(grouped), *outputPath)
   }
   ```

2. **Implement `groupByProduct`** function that:
   - Groups `RawDocument` entries by `ProductSlug`
   - Deduplicates pages with identical content (hash-based)
   - Concatenates unique page content with section separators
   - Extracts the product name from the first page title
   - Caps combined text at 50,000 characters per product (truncate overflow)

3. **Implement `decodeDocuments`** helper to handle Meilisearch SDK response format.

4. **Add a `Makefile` target:**
   ```makefile
   extract-catalog:
   	go run ./scripts/extract-catalog/extract.go \
   		-host $(MEILI_HOST) \
   		-key $(MEILI_KEY) \
   		-output data/raw-extract.json
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/meilisearch/meilisearch-go v0.29+` (verify latest stable as of March 2026)

## Acceptance Criteria
1. Running the script against a Meilisearch instance produces `data/raw-extract.json`
2. The output contains one entry per unique product (no duplicates)
3. Multi-page crawl results for the same product are merged into a single `combined_text`
4. Duplicate pages (by content hash) are excluded from the merge
5. Each product entry includes the source URLs for traceability
6. The script handles Meilisearch pagination correctly (works for any number of documents)
7. The script fails gracefully with a clear error if Meilisearch is unreachable
8. Combined text is capped at 50,000 characters per product

## Testing Requirements
- **Unit Tests:** Test `groupByProduct` with mock documents — verify deduplication, merging, and truncation. Test `decodeDocuments` with sample Meilisearch response data.
- **Integration Tests:** Run against a local Meilisearch with test data loaded via docker-compose.
- **Manual Verification:** Run `make extract-catalog`, inspect `data/raw-extract.json`, verify product count and content quality.

## Files to Create/Modify
- `scripts/extract-catalog/extract.go` — (create) Meilisearch extraction script
- `go.mod` — (modify) Add meilisearch-go dependency
- `Makefile` — (modify) Add `extract-catalog` target

## Risks & Edge Cases
- Meilisearch index may not use `product_slug` as the field name — the field mapping must be configurable or documented.
- Some products may have very few crawled pages (sparse data) — the enrichment step (TASK-021) must handle thin data gracefully.
- Meilisearch Go SDK versioning: the document retrieval API may differ across versions. Pin the SDK version explicitly.
- Network timeouts against remote Meilisearch: add a context with 30s timeout for each paginated request.

## Notes
- This script runs once during catalog setup, not at runtime. It's a build-time tool.
- The output `data/raw-extract.json` is an intermediate artifact — it feeds into the LLM enrichment pipeline (TASK-021). It should NOT be committed to the repo (add to `.gitignore`).
- If Meilisearch is not available, the enrichment step can work from a manually curated input file.
