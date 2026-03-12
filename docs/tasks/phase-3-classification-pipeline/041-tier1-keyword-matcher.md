# TASK-041: Tier 1 — Keyword and Alias Matcher

## Metadata
- **Phase:** 3
- **Module:** tier1
- **Priority:** P0-critical
- **Estimated Effort:** 2-3 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010, TASK-011, TASK-022, TASK-040]
- **Blocks:** [TASK-046]
- **Related:** [TASK-023]

## Objective
Implement Tier 1 keyword and alias matching — the fastest classification path. This tier checks user input against the product alias index using exact match (longest-match-first strategy) and returns immediately with high confidence (0.98) when a match is found. This is the fast path that handles ~25-30% of queries in under 1ms.

## Design Reference
- See Design Doc §4.2 Tier 1: Keyword / Alias Match
- See Design Doc §4.2.1 Longest-Match-First Strategy

## Technical Requirements

### Inputs / Prerequisites
- TASK-040 complete (preprocessor for normalizing input)
- TASK-022 complete (catalog Store with alias index)
- TASK-010 complete (TierResult type)

### Implementation Details

1. **Create `internal/tier1/keyword.go`:**

   ```go
   package tier1

   import (
       "sort"
       "strings"

       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
       "github.com/kaseya/kairos/internal/preprocess"
   )

   // Matcher performs Tier 1 keyword and alias matching.
   type Matcher struct {
       store *catalog.Store

       // sortedAliases is a list of all aliases sorted by length (longest first)
       // for longest-match-first strategy.
       sortedAliases []aliasEntry
   }

   type aliasEntry struct {
       normalized string
       product    *catalog.Product
   }

   // NewMatcher creates a Tier 1 matcher backed by the catalog store.
   func NewMatcher(store *catalog.Store) *Matcher {
       m := &Matcher{store: store}
       m.buildSortedAliases()
       return m
   }

   // buildSortedAliases creates a sorted alias list for longest-match-first.
   func (m *Matcher) buildSortedAliases() {
       products := m.store.GetAllProducts()
       var entries []aliasEntry

       for i := range products {
           p := &products[i]
           // Add all aliases
           for _, alias := range p.Aliases {
               entries = append(entries, aliasEntry{
                   normalized: preprocess.NormalizeAlias(alias),
                   product:    p,
               })
           }
           // Add product name and ID as implicit aliases
           entries = append(entries, aliasEntry{
               normalized: preprocess.NormalizeAlias(p.ProductName),
               product:    p,
           })
           entries = append(entries, aliasEntry{
               normalized: preprocess.NormalizeAlias(p.ProductID),
               product:    p,
           })
       }

       // Sort by length descending (longest first)
       sort.Slice(entries, func(i, j int) bool {
           return len(entries[i].normalized) > len(entries[j].normalized)
       })

       m.sortedAliases = entries
   }

   // Match attempts to find an exact keyword/alias match in the input.
   // Uses longest-match-first strategy to prefer more specific matches.
   func (m *Matcher) Match(normalizedInput string) *classify.TierResult {
       // Strategy: check if any alias appears as a substring of the input,
       // preferring longer aliases (more specific matches).
       for _, entry := range m.sortedAliases {
           if containsWord(normalizedInput, entry.normalized) {
               return &classify.TierResult{
                   Matched:    true,
                   ProductID:  entry.product.ProductID,
                   Confidence: 0.98, // Exact alias match confidence
                   Method:     classify.MethodKeywordExact,
                   Candidates: []classify.ScoredCandidate{
                       {
                           ProductID:   entry.product.ProductID,
                           ProductName: entry.product.ProductName,
                           Category:    entry.product.Category,
                           Score:       0.98,
                       },
                   },
               }
           }
       }

       return &classify.TierResult{
           Matched: false,
           Method:  classify.MethodKeywordExact,
       }
   }

   // containsWord checks if the input contains the alias as a whole word
   // (not as a substring of a larger word).
   func containsWord(input, alias string) bool {
       idx := strings.Index(input, alias)
       if idx == -1 {
           return false
       }
       // Check word boundary before
       if idx > 0 && !isWordBoundary(input[idx-1]) {
           return false
       }
       // Check word boundary after
       end := idx + len(alias)
       if end < len(input) && !isWordBoundary(input[end]) {
           return false
       }
       return true
   }

   func isWordBoundary(b byte) bool {
       return b == ' ' || b == '-' || b == '_'
   }

   // Rebuild re-builds the sorted alias list after a catalog reload.
   func (m *Matcher) Rebuild() {
       m.buildSortedAliases()
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies

## Acceptance Criteria
1. Input `"help with kaseya vsa agent"` matches product `kaseya-vsa` with confidence 0.98
2. Input `"vsa"` matches `kaseya-vsa` (alias lookup)
3. Input `"my datto rmm is broken"` matches `datto-rmm`
4. Longest-match-first: `"kaseya vsa"` preferred over `"vsa"` when both are aliases
5. Word boundary enforcement: `"visa application"` does NOT match alias `"vsa"`
6. Empty input returns `Matched: false`
7. Matching is case-insensitive (input is pre-normalized)
8. `Rebuild()` updates the alias index after catalog hot-reload
9. Match latency < 1ms for the full alias list (~400 aliases)
10. Unit test coverage ≥ 90%

## Testing Requirements
- **Unit Tests:** Test exact matches, longest-match-first behavior, word boundary enforcement, empty input, no-match scenarios. Benchmark match latency.
- **Integration Tests:** Test with sample catalog data from TASK-023.
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/tier1/keyword.go` — (create) Exact keyword/alias matcher
- `internal/tier1/keyword_test.go` — (create) Comprehensive unit tests and benchmarks

## Risks & Edge Cases
- Alias `"it"` (for "IT Glue") could false-positive match many inputs containing the word "it". Mitigation: aliases shorter than 3 characters should require exact full-input match, not substring match.
- Multiple products sharing a common alias: the sorted list will match the first one found. The catalog should be curated to avoid ambiguous aliases.
- Unicode word boundaries: `isWordBoundary` only checks ASCII. If aliases or input contain Unicode, this needs expansion.

## Notes
- The confidence value 0.98 is the `KEYWORD_EXACT_CONFIDENCE` threshold from the config. In the final implementation, read this from the threshold config rather than hardcoding. For initial development, hardcoded is fine.
- The `Rebuild()` method supports catalog hot-reload (TASK-083).
