# TASK-021: LLM Enrichment Pipeline for Catalog

## Metadata
- **Phase:** 2
- **Module:** scripts
- **Priority:** P0-critical
- **Estimated Effort:** 3-5 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-020, TASK-011]
- **Blocks:** [TASK-022, TASK-024]
- **Related:** [TASK-023]

## Objective
Build the LLM enrichment script (`scripts/extract-catalog/enrich.go`) that takes the raw extracted product data and uses an LLM via Azure AI Foundry to generate aliases, signal phrases, embedding anchors, and disambiguation hints for each product. This transforms raw crawl data into the structured catalog schema.

## Design Reference
- See Design Doc §3.2 Data Pipeline — Enrich phase
- See Design Doc §3.1 Product Entry Schema (target output fields)

## Technical Requirements

### Inputs / Prerequisites
- TASK-020 complete (raw extraction output at `data/raw-extract.json`)
- TASK-011 complete (Product type as output target)
- Azure AI Foundry credentials configured

### Implementation Details

1. **Create `scripts/extract-catalog/enrich.go`** as a standalone CLI tool:

   ```go
   package main

   // (Note: this file shares the package with extract.go — use build tags
   // or separate into enrich/main.go if needed)
   ```

   Alternatively, create as `scripts/enrich-catalog/main.go`.

2. **LLM enrichment prompt template:**

   ```text
   You are an expert on Kaseya's product suite. Given the following product documentation,
   generate a structured catalog entry.

   Product: {{.ProductName}}
   Documentation excerpt (truncated to 8000 chars):
   {{.CombinedText}}

   Generate the following fields as JSON:

   {
     "product_id": "lowercase-hyphenated-slug",
     "product_name": "Official Product Name",
     "category": "one of: RMM, PSA, Backup, Security, Networking, ITSM, Compliance, Identity, Other",
     "description": "1-2 sentence summary of what this product does",
     "aliases": ["list", "of", "5-10", "alternate names", "abbreviations", "common misspellings"],
     "signal_phrases": ["list", "of", "10-15", "user language phrases", "that indicate this product"],
     "embedding_anchors": ["3-5 carefully crafted sentences optimized for semantic similarity matching"],
     "disambiguation_hints": "2-3 sentences explaining how this product differs from similar Kaseya products",
     "related_products": ["product-id-1", "product-id-2"]
   }

   Rules:
   - Aliases should include abbreviations, former product names, and common misspellings
   - Signal phrases should be in natural user language (how a support user would describe a problem)
   - Embedding anchors should be informationally dense sentences combining product name + function + domain
   - Disambiguation hints should specifically address products that could be confused with this one
   - related_products should use product_id format (lowercase-hyphenated)
   ```

3. **Processing flow:**
   - Read `data/raw-extract.json`
   - For each product, truncate combined text to 8000 characters
   - Send the enrichment prompt to Azure AI Foundry chat completions endpoint
   - Parse the JSON response from the LLM
   - Validate the parsed entry against `catalog.Product` schema
   - Write validated entries to `data/catalog-draft.json`
   - Log any products that failed enrichment for manual review

4. **Rate limiting and resilience:**
   - Process products sequentially with a 1-second delay between requests (respect API rate limits)
   - Retry failed LLM calls up to 3 times with exponential backoff (2s, 4s, 8s)
   - If a product fails all retries, log it and continue with remaining products
   - Write a `data/enrichment-failures.json` file listing products that need manual enrichment

5. **Add CLI flags:**
   - `--input` — path to raw extract JSON (default: `data/raw-extract.json`)
   - `--output` — path to enriched catalog draft (default: `data/catalog-draft.json`)
   - `--endpoint` — Azure AI Foundry endpoint
   - `--api-key` — Azure AI Foundry API key
   - `--model` — deployment name (default: `gpt-4o-mini`)
   - `--dry-run` — parse and validate only, don't call LLM
   - `--resume` — skip products already present in the output file (for crash recovery)

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/Azure/azure-sdk-for-go/sdk/ai/azopenai` — latest stable (for chat completions)
- `github.com/Azure/azure-sdk-for-go/sdk/azcore` — latest stable

## Acceptance Criteria
1. Running the script produces `data/catalog-draft.json` with entries for all extracted products
2. Each entry conforms to the `catalog.Product` schema with all required fields populated
3. LLM-generated aliases include at least 5 entries per product
4. LLM-generated signal phrases include at least 10 entries per product
5. LLM-generated embedding anchors include at least 3 entries per product
6. Failed products are logged to `data/enrichment-failures.json` with error details
7. The `--resume` flag correctly skips already-enriched products
8. The `--dry-run` flag validates existing output without making LLM calls

## Testing Requirements
- **Unit Tests:** Test prompt template rendering with mock data. Test JSON response parsing with sample LLM outputs (valid and malformed). Test resume logic.
- **Integration Tests:** Run against Azure AI Foundry with a single test product to verify end-to-end flow.
- **Manual Verification:** Review `data/catalog-draft.json` for quality of generated aliases, signals, and anchors. This requires human judgment.

## Files to Create/Modify
- `scripts/enrich-catalog/main.go` — (create) LLM enrichment script
- `go.mod` — (modify) Add Azure AI SDK dependency
- `Makefile` — (modify) Add `enrich-catalog` target

## Risks & Edge Cases
- LLM may produce invalid JSON — implement robust JSON extraction from the response (look for JSON block within markdown code fences).
- LLM may hallucinate product names or aliases that don't exist — the manual review step (not automated) catches this.
- Azure AI Foundry rate limits may throttle requests — the 1-second delay and retry logic mitigate this.
- Token limits: if the combined text + prompt exceeds the model's context window, truncation must be applied. 8000 chars of input text + prompt ≈ 3000 tokens, well within limits.
- The `related_products` field depends on knowledge of other product IDs — run the enrichment in two passes if needed (first pass generates IDs, second pass fills related_products).

## Notes
- The output `data/catalog-draft.json` is a draft that requires human review before becoming the final `data/catalog.json`. The human review step is not automated — it's a manual process documented in the README.
- This script is run once during initial catalog setup and occasionally when new products are added. It is not a runtime component.
