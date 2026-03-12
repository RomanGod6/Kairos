# TASK-011: Product Catalog Schema and Types

## Metadata
- **Phase:** 1
- **Module:** catalog
- **Priority:** P0-critical
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001]
- **Blocks:** [TASK-020, TASK-021, TASK-022, TASK-041, TASK-042]
- **Related:** [TASK-010]

## Objective
Define the Go types for the product catalog schema — the data structure that represents each of the 44 Kaseya products with their aliases, signal phrases, embedding anchors, and disambiguation hints. This schema is the single source of truth consumed by all three classification tiers.

## Design Reference
- See Design Doc §3 Product Catalog Schema
- See Design Doc §3.1 Product Entry Schema

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (Go module)

### Implementation Details

1. **Create `internal/catalog/types.go`:**

   ```go
   package catalog

   // Catalog is the top-level container for all products.
   type Catalog struct {
       Version  string    `json:"version"`
       Products []Product `json:"products"`
   }

   // Product represents a single Kaseya product in the catalog.
   type Product struct {
       // ProductID is the unique, URL-safe identifier (e.g., "kaseya-vsa").
       ProductID string `json:"product_id"`

       // ProductName is the official display name (e.g., "Kaseya VSA").
       ProductName string `json:"product_name"`

       // Category groups the product (e.g., "RMM", "PSA", "Backup", "Security").
       Category string `json:"category"`

       // Description is a 1-2 sentence summary of what the product does.
       Description string `json:"description"`

       // Aliases are alternate names, abbreviations, and common misspellings
       // used for Tier 1 keyword matching.
       // Example: ["VSA", "vsa", "Kaseya RMM", "KRMS"]
       Aliases []string `json:"aliases"`

       // SignalPhrases are user-language phrases that strongly indicate this product.
       // Used for Tier 1 fuzzy matching and Tier 2 embedding anchors.
       // Example: ["endpoints not checking in", "agent offline", "patch management"]
       SignalPhrases []string `json:"signal_phrases"`

       // EmbeddingAnchors are carefully crafted sentences optimized for embedding similarity.
       // Each anchor is embedded and the max similarity across anchors is used as the product score.
       // Example: ["Kaseya VSA is a remote monitoring and management platform for IT endpoints"]
       EmbeddingAnchors []string `json:"embedding_anchors"`

       // DisambiguationHints help the Tier 3 reranker distinguish this product
       // from similar products.
       // Example: "VSA focuses on endpoint management, not network monitoring"
       DisambiguationHints string `json:"disambiguation_hints"`

       // RelatedProducts lists product IDs that are commonly confused with this one.
       // Used by the reranker to generate more targeted prompts.
       RelatedProducts []string `json:"related_products,omitempty"`
   }

   // EmbeddingCache holds pre-computed embeddings for all product anchors.
   type EmbeddingCache struct {
       ModelID    string                `json:"model_id"`
       Dimensions int                   `json:"dimensions"`
       Products   []ProductEmbeddings   `json:"products"`
   }

   // ProductEmbeddings holds all embedding vectors for a single product.
   type ProductEmbeddings struct {
       ProductID  string      `json:"product_id"`
       Anchors    []AnchorEmbedding `json:"anchors"`
   }

   // AnchorEmbedding is a single embedding anchor text paired with its vector.
   type AnchorEmbedding struct {
       Text      string    `json:"text"`
       Vector    []float64 `json:"vector"`
   }

   // ThresholdConfig holds tunable confidence thresholds loaded from file.
   type ThresholdConfig struct {
       KeywordExactConfidence     float64 `json:"keyword_exact_confidence"`
       KeywordFuzzyConfidence     float64 `json:"keyword_fuzzy_confidence"`
       SemanticHighThreshold      float64 `json:"semantic_high_threshold"`
       SemanticMinGap             float64 `json:"semantic_min_gap"`
       SemanticAmbiguousThreshold float64 `json:"semantic_ambiguous_threshold"`
       SemanticNoMatchThreshold   float64 `json:"semantic_no_match_threshold"`
       RerankerConfidenceFloor    float64 `json:"reranker_confidence_floor"`
   }
   ```

2. **Add validation methods:**

   ```go
   import "fmt"

   // Validate checks that a Product has all required fields populated.
   func (p *Product) Validate() error {
       if p.ProductID == "" {
           return fmt.Errorf("product_id is required")
       }
       if p.ProductName == "" {
           return fmt.Errorf("product %q: product_name is required", p.ProductID)
       }
       if p.Category == "" {
           return fmt.Errorf("product %q: category is required", p.ProductID)
       }
       if len(p.Aliases) == 0 {
           return fmt.Errorf("product %q: at least one alias is required", p.ProductID)
       }
       if len(p.EmbeddingAnchors) == 0 {
           return fmt.Errorf("product %q: at least one embedding_anchor is required", p.ProductID)
       }
       return nil
   }

   // Validate checks the catalog integrity.
   func (c *Catalog) Validate() error {
       if len(c.Products) == 0 {
           return fmt.Errorf("catalog is empty")
       }
       seen := make(map[string]bool)
       for i, p := range c.Products {
           if err := p.Validate(); err != nil {
               return fmt.Errorf("product[%d]: %w", i, err)
           }
           if seen[p.ProductID] {
               return fmt.Errorf("duplicate product_id: %q", p.ProductID)
           }
           seen[p.ProductID] = true
       }
       return nil
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies

## Acceptance Criteria
1. All catalog types compile and serialize to JSON matching the expected `catalog.json` format
2. `Product.Validate()` rejects products missing required fields
3. `Catalog.Validate()` rejects empty catalogs and duplicate product IDs
4. `EmbeddingCache` types support multi-anchor-per-product storage with float64 vectors
5. JSON tags use lowercase snake_case consistent with the catalog data files
6. Unit tests cover all validation edge cases

## Testing Requirements
- **Unit Tests:** Test `Validate()` for products with missing fields, duplicate IDs, empty catalogs. Test JSON round-trip for all types.
- **Integration Tests:** None — data types only
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/catalog/types.go` — (create) Catalog, Product, EmbeddingCache types
- `internal/catalog/types_test.go` — (create) Validation and serialization tests

## Risks & Edge Cases
- The `Vector` field in `AnchorEmbedding` uses `[]float64` which is accurate for most embedding models. If a model returns `float32`, conversion is needed during loading.
- Catalog with 44 products × ~5 anchors × 1536 dimensions ≈ 330K float64 values ≈ 2.5 MB in memory. This is negligible.
- `DisambiguationHints` is a single string, not a slice. This is intentional — it's a free-form paragraph used in the reranker prompt.

## Notes
- The `ThresholdConfig` type here mirrors the one in `internal/config/`. This is intentional — the config package holds the defaults loaded from env vars, while this file-based version supports hot-reload from `data/thresholds.json`. The catalog loader (TASK-022) will merge them.
