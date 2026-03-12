# TASK-083: Catalog Hot-Reload Endpoint

## Metadata
- **Phase:** 5
- **Module:** catalog
- **Priority:** P2-medium
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-022, TASK-041, TASK-061]
- **Blocks:** [TASK-084]
- **Related:** None

## Objective
Implement an admin endpoint `POST /admin/reload-catalog` that triggers a live reload of the product catalog and embeddings from disk without restarting the service. This enables catalog updates, threshold tuning, and embedding regeneration without downtime.

## Design Reference
- See Design Doc §7.4 Catalog Hot-Reload
- See Design Doc §3.4 Catalog Loading (reload strategy)

## Technical Requirements

### Inputs / Prerequisites
- TASK-022 complete (catalog Store with RWMutex)
- TASK-041 complete (Tier 1 matcher with Rebuild method)
- TASK-061 complete (auth middleware for admin endpoints)

### Implementation Details

1. **Create reload handler:**

   ```go
   func ReloadCatalogHandler(store *catalog.Store, matcher *tier1.Matcher, cfg *config.Config) http.HandlerFunc {
       return func(w http.ResponseWriter, r *http.Request) {
           log := zerolog.Ctx(r.Context())

           // Reload catalog
           if err := store.LoadCatalog(cfg.Catalog.CatalogPath); err != nil {
               log.Error().Err(err).Msg("catalog reload failed")
               WriteInternalError(w, r, "catalog reload failed: "+err.Error())
               return
           }

           // Reload embeddings
           if err := store.LoadEmbeddings(cfg.Catalog.EmbeddingsPath); err != nil {
               log.Error().Err(err).Msg("embeddings reload failed")
               WriteInternalError(w, r, "embeddings reload failed: "+err.Error())
               return
           }

           // Rebuild Tier 1 alias index
           matcher.Rebuild()

           log.Info().
               Int("products", store.ProductCount()).
               Msg("catalog reloaded successfully")

           WriteJSON(w, http.StatusOK, map[string]interface{}{
               "status":   "reloaded",
               "products": store.ProductCount(),
           })
       }
   }
   ```

2. **Register admin routes** under `/admin/` with authentication:

   ```go
   r.Route("/admin", func(r chi.Router) {
       r.Use(AuthMiddleware(cfg.Server.APIKey))
       r.Post("/reload-catalog", ReloadCatalogHandler(store, matcher, cfg))
   })
   ```

3. **Ensure thread safety:** The `catalog.Store` uses `sync.RWMutex`. During reload, write lock is held. In-flight classification requests using the old catalog complete normally (they hold read locks). New requests after the write lock is released see the new catalog.

### Tech Stack & Dependencies
- `go 1.22+`

## Acceptance Criteria
1. `POST /admin/reload-catalog` reloads catalog and embeddings from disk
2. The reload is atomic — requests never see a partially loaded catalog
3. In-flight requests complete with the old catalog data
4. New requests after reload see the new catalog data
5. Failed reload does not corrupt the existing catalog (old data remains)
6. Endpoint requires authentication
7. Response includes product count after reload
8. Tier 1 alias index is rebuilt after catalog reload

## Testing Requirements
- **Unit Tests:** Test reload with valid/invalid files. Test concurrent read/reload with -race flag.
- **Integration Tests:** Start server, classify a product, update catalog file, reload, classify again, verify new data is used.
- **Manual Verification:** `curl -X POST -H "Authorization: Bearer <key>" http://localhost:8080/admin/reload-catalog`

## Files to Create/Modify
- `internal/api/handler.go` — (modify) Add ReloadCatalogHandler
- `internal/api/routes.go` — (modify) Register admin routes

## Risks & Edge Cases
- If the new catalog file is malformed, the reload fails and the old catalog remains active. This is the correct behavior.
- During reload, there's a brief period where the write lock blocks new reads. For 44 products, the reload takes <100ms, so the impact is negligible.
- Tier 2 semantic matcher references the store's embeddings. After store reload, Tier 2 automatically sees new embeddings through the store's accessor methods.

## Notes
- This endpoint should be used sparingly — primarily for threshold tuning and catalog updates. It's not designed for high-frequency calls.
