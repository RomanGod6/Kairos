# TASK-040: Text Preprocessor

## Metadata
- **Phase:** 3
- **Module:** preprocess
- **Priority:** P0-critical
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-010]
- **Blocks:** [TASK-041, TASK-042, TASK-046]
- **Related:** None

## Objective
Implement the text preprocessing module that normalizes raw user input before it enters the classification pipeline. This includes lowercasing, special character stripping, abbreviation expansion, whitespace normalization, and input length truncation. Consistent preprocessing is critical — both user queries and catalog aliases must be normalized the same way.

## Design Reference
- See Design Doc §4.1 Preprocessor
- See Design Doc §4.2 Tier 1 (preprocessing feeds keyword matching)

## Technical Requirements

### Inputs / Prerequisites
- TASK-010 complete (classification types available)

### Implementation Details

1. **Create `internal/preprocess/preprocess.go`:**

   ```go
   package preprocess

   import (
       "regexp"
       "strings"
       "unicode"
   )

   const maxInputLength = 2000

   // Known abbreviation expansions for IT/MSP domain.
   var abbreviations = map[string]string{
       "rmm":   "remote monitoring and management",
       "psa":   "professional services automation",
       "msp":   "managed service provider",
       "edr":   "endpoint detection and response",
       "siem":  "security information and event management",
       "bcdr":  "business continuity and disaster recovery",
       "mfa":   "multi-factor authentication",
       "sso":   "single sign-on",
       "noc":   "network operations center",
       "sla":   "service level agreement",
       "cmdb":  "configuration management database",
       "itil":  "information technology infrastructure library",
       "itsm":  "it service management",
   }

   var (
       // Matches sequences of non-alphanumeric, non-space characters
       specialCharsRe = regexp.MustCompile(`[^\w\s-]`)
       // Matches multiple consecutive whitespace characters
       multiSpaceRe = regexp.MustCompile(`\s+`)
   )

   // NormalizeQuery applies the full preprocessing pipeline to a user query.
   func NormalizeQuery(input string) string {
       // 1. Truncate to max length
       if len(input) > maxInputLength {
           input = input[:maxInputLength]
       }

       // 2. Lowercase
       input = strings.ToLower(input)

       // 3. Strip special characters (keep alphanumeric, spaces, hyphens)
       input = specialCharsRe.ReplaceAllString(input, " ")

       // 4. Normalize whitespace
       input = multiSpaceRe.ReplaceAllString(input, " ")
       input = strings.TrimSpace(input)

       return input
   }

   // ExpandAbbreviations expands known IT/MSP abbreviations in the input.
   // Returns the expanded text and the original for dual-matching.
   func ExpandAbbreviations(input string) (expanded string, original string) {
       original = input
       words := strings.Fields(input)
       changed := false
       for i, w := range words {
           if exp, ok := abbreviations[w]; ok {
               words[i] = exp
               changed = true
           }
       }
       if changed {
           expanded = strings.Join(words, " ")
       } else {
           expanded = input
       }
       return expanded, original
   }

   // NormalizeAlias applies the same normalization to a catalog alias
   // as is applied to user queries, ensuring consistent matching.
   func NormalizeAlias(alias string) string {
       return strings.ToLower(strings.TrimSpace(alias))
   }

   // ExtractKeyTerms splits normalized input into individual terms for matching.
   func ExtractKeyTerms(input string) []string {
       words := strings.Fields(input)
       var terms []string
       for _, w := range words {
           if len(w) >= 2 { // Skip single-character noise
               terms = append(terms, w)
           }
       }
       return terms
   }
   ```

### Tech Stack & Dependencies
- `go 1.22+`
- No additional dependencies (standard library only)

## Acceptance Criteria
1. `NormalizeQuery("My Endpoints Aren't Checking In!!!")` returns `"my endpoints arent checking in"`
2. `NormalizeQuery` truncates input over 2000 characters
3. `ExpandAbbreviations("need help with rmm")` returns `("need help with remote monitoring and management", "need help with rmm")`
4. `NormalizeAlias("Kaseya VSA")` returns `"kaseya vsa"`
5. `ExtractKeyTerms("my vsa agent is offline")` returns `["my", "vsa", "agent", "is", "offline"]`
6. Special characters (punctuation, emojis) are stripped
7. Multiple spaces are collapsed to single spaces
8. Unit test coverage ≥ 95% for the preprocess package

## Testing Requirements
- **Unit Tests:** Test every function with diverse inputs: empty string, Unicode, emojis, extremely long strings, strings with only special characters, abbreviation edge cases (partial matches should NOT expand).
- **Integration Tests:** None needed — pure functions
- **Manual Verification:** None needed

## Files to Create/Modify
- `internal/preprocess/preprocess.go` — (create) Text preprocessing functions
- `internal/preprocess/preprocess_test.go` — (create) Comprehensive unit tests

## Risks & Edge Cases
- Unicode handling: `strings.ToLower` handles Unicode correctly, but the special character regex should preserve Unicode letters (not just ASCII). Use `\w` which is Unicode-aware in Go's regexp.
- Abbreviation expansion should only match whole words, not substrings. `"prism"` should not match `"psa"`.
- Hyphenated product names: "IT Glue" vs "it-glue" — the hyphen is preserved by the regex, so both forms are kept. Ensure Tier 1 handles both.
- Empty input after normalization should return an empty string (not error).

## Notes
- The abbreviation map will grow over time based on real user query patterns. Consider loading it from a configuration file rather than hardcoding it, but for now hardcoded is acceptable.
- The `NormalizeAlias` function is intentionally simpler than `NormalizeQuery` — aliases in the catalog are already clean, they just need lowercasing.
