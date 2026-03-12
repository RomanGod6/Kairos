# TASK-023: Sample Catalog and Embedding Data Files

## Metadata
- **Phase:** 2
- **Module:** catalog
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-011]
- **Blocks:** [TASK-041, TASK-042, TASK-043, TASK-045, TASK-100]
- **Related:** [TASK-021, TASK-022]

## Objective
Create well-structured sample `data/catalog.json`, `data/embeddings.json`, and `data/thresholds.json` files with realistic data for at least 10 products. These samples enable development and testing of all tiers before the full catalog enrichment pipeline is complete.

## Design Reference
- See Design Doc §3.1 Product Entry Schema
- See Design Doc §3.5 Embedding Cache Format
- See Design Doc §5.3 Confidence Thresholds

## Technical Requirements

### Inputs / Prerequisites
- TASK-011 complete (catalog types defined for schema reference)

### Implementation Details

1. **Create `data/catalog.json`** with at least 10 representative products spanning different categories:

   ```json
   {
     "version": "1.0.0-sample",
     "products": [
       {
         "product_id": "kaseya-vsa",
         "product_name": "Kaseya VSA",
         "category": "RMM",
         "description": "Remote monitoring and management platform for IT endpoints, providing patch management, remote control, and automated IT workflows.",
         "aliases": ["VSA", "vsa", "Kaseya RMM", "KRMS", "Virtual System Administrator"],
         "signal_phrases": ["endpoints not checking in", "agent offline", "patch management", "remote control", "monitoring dashboard", "automated remediation", "endpoint management"],
         "embedding_anchors": [
           "Kaseya VSA is a remote monitoring and management platform for managing IT endpoints including desktops servers and network devices",
           "VSA provides automated patch management remote control and IT workflow automation for managed service providers",
           "Kaseya VSA monitors endpoint health deploys patches and enables remote troubleshooting of Windows Mac and Linux machines"
         ],
         "disambiguation_hints": "VSA focuses on endpoint management and RMM. It is not Datto RMM (a separate RMM product) and not IT Glue (which is documentation). VSA handles agents, patches, and remote sessions.",
         "related_products": ["datto-rmm", "it-glue"]
       }
       // ... 9 more products covering PSA, Backup, Security, Networking, etc.
     ]
   }
   ```

2. **Create `data/embeddings.json`** with placeholder vectors (1536-dimensional zero vectors or random vectors for testing). These will be replaced with real embeddings from TASK-024.

   ```json
   {
     "model_id": "text-embedding-3-small",
     "dimensions": 1536,
     "products": [
       {
         "product_id": "kaseya-vsa",
         "anchors": [
           {
             "text": "Kaseya VSA is a remote monitoring and management platform...",
             "vector": [0.01, -0.02, 0.03, ...]
           }
         ]
       }
     ]
   }
   ```

3. **Create `data/thresholds.json`:**

   ```json
   {
     "keyword_exact_confidence": 0.98,
     "keyword_fuzzy_confidence": 0.85,
     "semantic_high_threshold": 0.78,
     "semantic_min_gap": 0.08,
     "semantic_ambiguous_threshold": 0.65,
     "semantic_no_match_threshold": 0.65,
     "reranker_confidence_floor": 0.70
   }
   ```

4. **Include products from diverse categories:** RMM (VSA, Datto RMM), PSA (BMS, Autotask), Backup (Datto BCDR, Unitrends), Security (RocketCyber, Graphus), Networking (Datto Networking), Documentation (IT Glue).

### Tech Stack & Dependencies
- None — these are static JSON files

## Acceptance Criteria
1. `data/catalog.json` contains at least 10 products with all required fields populated
2. `data/catalog.json` passes validation via `Catalog.Validate()` from TASK-011
3. `data/embeddings.json` has matching entries for all products in the catalog
4. `data/thresholds.json` contains all threshold values with defaults matching the design doc
5. Products span at least 5 different categories
6. Each product has at least 5 aliases, 7 signal phrases, and 3 embedding anchors
7. The sample data is realistic enough to test Tier 1 keyword matching

## Testing Requirements
- **Unit Tests:** Write a test that loads `data/catalog.json` using `Store.LoadCatalog()` and verifies it passes validation.
- **Integration Tests:** None
- **Manual Verification:** Review catalog entries for accuracy against known Kaseya product information.

## Files to Create/Modify
- `data/catalog.json` — (create) Sample product catalog
- `data/embeddings.json` — (create) Placeholder embedding vectors
- `data/thresholds.json` — (create) Default confidence thresholds

## Risks & Edge Cases
- Sample embeddings with zero/random vectors will not produce meaningful cosine similarity. Tier 2 tests should use controlled vectors that produce known similarity scores.
- Product information accuracy: the sample data is for development only and will be replaced by the enrichment pipeline output. Don't over-invest in perfecting it.

## Notes
- The full 44-product catalog will come from the TASK-020 → TASK-021 extraction/enrichment pipeline. These sample files bridge the gap for Phases 3-4 development.
- Consider generating the placeholder embedding vectors programmatically (a small script) rather than hand-writing 1536-dimensional vectors.
