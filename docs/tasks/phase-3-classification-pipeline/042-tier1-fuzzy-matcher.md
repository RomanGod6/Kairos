# TASK-042: Tier 1 — Fuzzy Match with Levenshtein Distance

## Metadata
- **Phase:** 3
- **Module:** tier1
- **Priority:** P1-high
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010, TASK-011, TASK-022, TASK-040, TASK-041]
- **Blocks:** [TASK-046]
- **Related:** [TASK-023]

## Objective
Extend Tier 1 with fuzzy matching using Levenshtein distance for near-miss alias matches (e.g., "Kasey VSA" → "Kaseya VSA", edit distance = 1). This catches common typos and misspellings that exact matching misses, returning with confidence 0.85.

## Design Reference
- See Design Doc §4.2 Tier 1: Keyword / Alias Match — Fuzzy Fallback
- See Design Doc §5.3 Confidence Thresholds (KEYWORD_FUZZY_CONFIDENCE = 0.85)

## Technical Requirements

### Inputs / Prerequisites
- TASK-041 complete (exact matcher exists)
- TASK-040 complete (preprocessor)
- TASK-022 complete (catalog Store)

### Implementation Details

1. **Create `internal/tier1/fuzzy.go`:**

   ```go
   package tier1

   import (
       "github.com/agnivade/levenshtein"
       "github.com/kaseya/kairos/internal/catalog"
       "github.com/kaseya/kairos/internal/classify"
       "github.com/kaseya/kairos/internal/preprocess"
   )

   const (
       maxEditDistance = 2
       minAliasLengthForFuzzy = 4 // Don't fuzzy match very short aliases
   )

   // FuzzyMatch attempts to find a near-match when exact matching fails.
   // It compares each word/phrase in the input against all aliases using
   // Levenshtein distance with a max edit distance of 2.
   func (m *Matcher) FuzzyMatch(normalizedInput string) *classify.TierResult {
       terms := preprocess.ExtractKeyTerms(normalizedInput)

       var bestMatch *catalog.Product
       bestDistance := maxEditDistance + 1
       bestAlias := ""

       // Check each input term and multi-word combination against aliases
       for _, entry := range m.sortedAliases {
           if len(entry.normalized) < minAliasLengthForFuzzy {
               continue
           }

           // Check individual terms
           for _, term := range terms {
               dist := levenshtein.ComputeDistance(term, entry.normalized)
               if dist <= maxEditDistance && dist < bestDistance {
                   bestDistance = dist
                   bestMatch = entry.product
                   bestAlias = entry.normalized
               }
           }

           // Check sliding windows of multi-word phrases matching alias word count
           aliasWordCount := len(preprocess.ExtractKeyTerms(entry.normalized))
           if aliasWordCount > 1 && len(terms) >= aliasWordCount {
               for i := 0; i <= len(terms)-aliasWordCount; i++ {
                   phrase := joinTerms(terms[i : i+aliasWordCount])
                   dist := levenshtein.ComputeDistance(phrase, entry.normalized)
                   if dist <= maxEditDistance && dist < bestDistance {
                       bestDistance = dist
                       bestMatch = entry.product
                       bestAlias = entry.normalized
                   }
               }
           }
       }

       if bestMatch != nil {
           return &classify.TierResult{
               Matched:    true,
               ProductID:  bestMatch.ProductID,
               Confidence: 0.85, // Fuzzy match confidence
               Method:     classify.MethodKeywordFuzzy,
               Candidates: []classify.ScoredCandidate{
                   {
                       ProductID:   bestMatch.ProductID,
                       ProductName: bestMatch.ProductName,
                       Category:    bestMatch.Category,
                       Score:       0.85,
                   },
               },
           }
       }

       return &classify.TierResult{
           Matched: false,
           Method:  classify.MethodKeywordFuzzy,
       }
   }

   func joinTerms(terms []string) string {
       result := terms[0]
       for _, t := range terms[1:] {
           result += " " + t
       }
       return result
   }
   ```

2. **Integrate into the `Matcher`** so the pipeline can call `Match()` first, then `FuzzyMatch()` if exact matching fails.

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/agnivade/levenshtein v1.2+` (verify latest stable as of March 2026)

## Acceptance Criteria
1. `FuzzyMatch("kasey vsa agent")` matches `kaseya-vsa` (edit distance 1 for "kasey" → "kaseya")
2. `FuzzyMatch("dato rmm")` matches `datto-rmm` (edit distance 1 for "dato" → "datto")
3. Edit distance > 2 does NOT produce a match
4. Short aliases (< 4 characters) are excluded from fuzzy matching to prevent false positives
5. Multi-word alias fuzzy matching works (e.g., "Kaseya VSE" → "Kaseya VSA", distance 1)
6. Confidence is always 0.85 for fuzzy matches
7. Fuzzy match latency < 5ms for the full alias list
8. Unit test coverage ≥ 90%

## Testing Requirements
- **Unit Tests:** Test typo corrections, multi-word fuzzy matching, distance threshold enforcement, short alias exclusion. Benchmark latency.
- **Integration Tests:** Test with sample catalog from TASK-023.
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/tier1/fuzzy.go` — (create) Levenshtein fuzzy matching
- `internal/tier1/fuzzy_test.go` — (create) Unit tests and benchmarks
- `go.mod` — (modify) Add levenshtein dependency

## Risks & Edge Cases
- Performance: Levenshtein is O(n*m) per comparison. With ~400 aliases and ~10 input terms, worst case is ~4000 comparisons. Each is sub-microsecond for short strings, so total < 5ms.
- False positives: `"bat"` (edit distance 1 from `"bms"`) — the `minAliasLengthForFuzzy` guard prevents this.
- If two aliases have the same edit distance from a term, the first one in the sorted list wins (longest alias). This is acceptable.

## Notes
- The confidence value 0.85 should be read from config in the final implementation. Hardcoded for initial development.
- Consider adding a small confidence penalty proportional to edit distance (e.g., 0.85 for distance 1, 0.80 for distance 2) in a future iteration.
