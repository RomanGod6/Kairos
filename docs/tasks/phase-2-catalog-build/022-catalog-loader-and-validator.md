# TASK-022: Catalog Loader, Validator, and In-Memory Store

## Metadata
- **Phase:** 2
- **Module:** catalog
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-002, TASK-011]
- **Blocks:** [TASK-041, TASK-042, TASK-046, TASK-083]
- **Related:** [TASK-004, TASK-021]

## Objective
Implement the catalog loader that reads `data/catalog.json` and `data/embeddings.json` at startup, validates all entries, and holds them in an efficiently indexed in-memory store. This is the runtime data backbone that Tier 1, Tier 2, and Tier 3 all query.

## Design Reference
- See Design Doc §3.4 Catalog Loading (startup flow)
- See Design Doc §3.1 Product Entry Schema (validation rules)

## Technical Requirements

### Inputs / Prerequisites
- TASK-011 complete (catalog types defined)
- TASK-002 complete (config with file paths)
- A valid `data/catalog.json` file (produced by TASK-021 enrichment + human review)

### Implementation Details

1. **Create `internal/catalog/loader.go`:**

   ```go
   package catalog

   import (
       "encoding/json"
       "fmt"
       "os"
       "sync"
   )

   // Store holds the loaded catalog and embeddings in memory
   // with indexed lookups for fast access by all tiers.
   type Store struct {
       mu sync.RWMutex

       // catalog is the raw loaded catalog
       catalog *Catalog

       // byID maps product_id → *Product for O(1) lookup
       byID map[string]*Product

       // byAlias maps lowercase alias → *Product for Tier 1
       byAlias map[string]*Product

       // embeddings holds pre-computed product embeddings for Tier 2
       embeddings *EmbeddingCache

       // embeddingsByProduct maps product_id → []AnchorEmbedding for Tier 2
       embeddingsByProduct map[string][]AnchorEmbedding
   }

   // NewStore creates an empty catalog store.
   func NewStore() *Store {
       return &Store{
           byID:                make(map[string]*Product),
           byAlias:             make(map[string]*Product),
           embeddingsByProduct: make(map[string][]AnchorEmbedding),
       }
   }

   // LoadCatalog reads and validates the product catalog from a JSON file.
   func (s *Store) LoadCatalog(path string) error {
       data, err := os.ReadFile(path)
       if err != nil {
           return fmt.Errorf("reading catalog file %s: %w", path, err)
       }

       var cat Catalog
       if err := json.Unmarshal(data, &cat); err != nil {
           return fmt.Errorf("parsing catalog JSON: %w", err)
       }

       if err := cat.Validate(); err != nil {
           return fmt.Errorf("validating catalog: %w", err)
       }

       s.mu.Lock()
       defer s.mu.Unlock()

       s.catalog = &cat
       s.byID = make(map[string]*Product, len(cat.Products))
       s.byAlias = make(map[string]*Product, len(cat.Products)*8) // ~8 aliases per product

       for i := range cat.Products {
           p := &cat.Products[i]
           s.byID[p.ProductID] = p
           // Index all aliases as lowercase for case-insensitive lookup
           for _, alias := range p.Aliases {
               s.byAlias[strings.ToLower(alias)] = p
           }
           // Also index product name and product ID as aliases
           s.byAlias[strings.ToLower(p.ProductName)] = p
           s.byAlias[strings.ToLower(p.ProductID)] = p
       }

       return nil
   }

   // LoadEmbeddings reads pre-computed embeddings from a JSON file.
   func (s *Store) LoadEmbeddings(path string) error {
       data, err := os.ReadFile(path)
       if err != nil {
           return fmt.Errorf("reading embeddings file %s: %w", path, err)
       }

       var cache EmbeddingCache
       if err := json.Unmarshal(data, &cache); err != nil {
           return fmt.Errorf("parsing embeddings JSON: %w", err)
       }

       s.mu.Lock()
       defer s.mu.Unlock()

       s.embeddings = &cache
       s.embeddingsByProduct = make(map[string][]AnchorEmbedding, len(cache.Products))
       for _, pe := range cache.Products {
           s.embeddingsByProduct[pe.ProductID] = pe.Anchors
       }

       return nil
   }

   // GetProductByID returns a product by its ID, or nil if not found.
   func (s *Store) GetProductByID(id string) *Product {
       s.mu.RLock()
       defer s.mu.RUnlock()
       return s.byID[id]
   }

   // GetProductByAlias returns a product by alias (case-insensitive).
   func (s *Store) GetProductByAlias(alias string) *Product {
       s.mu.RLock()
       defer s.mu.RUnlock()
       return s.byAlias[strings.ToLower(alias)]
   }

   // GetAllProducts returns all products in the catalog.
   func (s *Store) GetAllProducts() []Product {
       s.mu.RLock()
       defer s.mu.RUnlock()
       if s.catalog == nil {
           return nil
       }
       return s.catalog.Products
   }

   // GetEmbeddings returns the anchor embeddings for a product.
   func (s *Store) GetEmbeddings(productID string) []AnchorEmbedding {
       s.mu.RLock()
       defer s.mu.RUnlock()
       return s.embeddingsByProduct[productID]
   }

   // GetAllEmbeddings returns the full embedding cache.
   func (s *Store) GetAllEmbeddings() *EmbeddingCache {
       s.mu.RLock()
       defer s.mu.RUnlock()
       return s.embeddings
   }

   // ProductCount returns the number of loaded products.
   func (s *Store) ProductCount() int {
       s.mu.RLock()
       defer s.mu.RUnlock()
       if s.catalog == nil {
           return 0
       }
       return len(s.catalog.Products)
   }
   ```

2. **Wire catalog loading into `cmd/server/main.go`:**
   - Load catalog and embeddings before starting HTTP server
   - Log product count and embedding dimensions
   - Set readiness state to true after successful load
   - If catalog loading fails, log error and exit with code 1

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies (standard library JSON + OS)

## Acceptance Criteria
1. `Store.LoadCatalog()` successfully loads and indexes a valid `catalog.json`
2. `Store.LoadEmbeddings()` successfully loads embedding vectors
3. `GetProductByAlias("VSA")` returns the correct product (case-insensitive)
4. `GetProductByAlias("vsa")` returns the same product as `GetProductByAlias("VSA")`
5. `GetProductByID("kaseya-vsa")` returns the correct product
6. Invalid catalog files (missing fields, duplicates) cause `LoadCatalog` to return an error
7. The store is thread-safe — concurrent reads are safe while a reload is in progress
8. The server exits with a clear error if catalog loading fails at startup
9. Unit test coverage ≥ 85% for the catalog package

## Testing Requirements
- **Unit Tests:** Test `LoadCatalog` with valid/invalid JSON files (use `os.CreateTemp`). Test all lookup methods. Test concurrent access with `go test -race`. Test `Validate` with edge cases.
- **Integration Tests:** Load the actual `data/catalog.json` (once it exists) and verify indexing.
- **Manual Verification:** Start the server, verify log output shows "loaded 44 products", check readiness endpoint.

## Files to Create/Modify
- `internal/catalog/loader.go` — (create) Catalog store with loading and indexing
- `internal/catalog/loader_test.go` — (create) Comprehensive unit tests
- `cmd/server/main.go` — (modify) Wire catalog loading into startup sequence

## Risks & Edge Cases
- Alias collisions: two products may share an alias (e.g., "backup" could match multiple products). The loader should log a warning but use first-match semantics. Tier 1 will handle this by preferring exact matches.
- Large embedding files: with 44 products × 5 anchors × 1536 dimensions, the JSON file will be ~15-20 MB. `os.ReadFile` handles this fine, but parsing takes ~200-500ms. Log the load time.
- File not found: clear error message distinguishing "file doesn't exist" from "file is malformed".

## Notes
- The `sync.RWMutex` enables the hot-reload feature (TASK-083) where the catalog can be replaced at runtime without stopping the server.
- The `strings.ToLower` normalization must match the preprocessing applied to user queries in Tier 1 (TASK-040).
