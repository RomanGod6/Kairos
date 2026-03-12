# TASK-002: Configuration Types and Environment Variable Parsing

## Metadata
- **Phase:** 1
- **Module:** config
- **Priority:** P0-critical
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001]
- **Blocks:** [TASK-003, TASK-006, TASK-007, TASK-008, TASK-009, TASK-022]
- **Related:** None

## Objective
Implement the centralized configuration module that loads all service settings from environment variables with sensible defaults and validation. This module is consumed by every other package in the system — it must be reliable, well-typed, and fail fast on invalid configuration.

## Design Reference
- See Design Doc §3 Configuration & Environment
- See Design Doc §6.1 Azure AI Foundry Configuration
- See Design Doc §5.3 Confidence Thresholds

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (Go module and directory structure exist)

### Implementation Details

1. **Create `internal/config/config.go`** with the following structures and loader:

   ```go
   package config

   import (
       "fmt"
       "os"
       "strconv"
       "time"

       "github.com/joho/godotenv"
   )

   // Config holds all application configuration.
   type Config struct {
       Server    ServerConfig
       AzureAI   AzureAIConfig
       Catalog   CatalogConfig
       Threshold ThresholdConfig
       RateLimit RateLimitConfig
       Log       LogConfig
   }

   // ServerConfig holds HTTP server settings.
   type ServerConfig struct {
       Port            int           `json:"port"`
       ReadTimeout     time.Duration `json:"read_timeout"`
       WriteTimeout    time.Duration `json:"write_timeout"`
       ShutdownTimeout time.Duration `json:"shutdown_timeout"`
       APIKey          string        `json:"-"` // never serialize
   }

   // AzureAIConfig holds Azure AI Foundry connection settings.
   type AzureAIConfig struct {
       Endpoint             string        `json:"endpoint"`
       APIKey               string        `json:"-"` // never serialize
       EmbeddingDeployment  string        `json:"embedding_deployment"`
       EmbeddingDimensions  int           `json:"embedding_dimensions"`
       RerankerDeployment   string        `json:"reranker_deployment"`
       RerankerMaxTokens    int           `json:"reranker_max_tokens"`
       RerankerTemperature  float64       `json:"reranker_temperature"`
       RerankerTimeout      time.Duration `json:"reranker_timeout"`
   }

   // CatalogConfig holds file paths for catalog data.
   type CatalogConfig struct {
       CatalogPath    string `json:"catalog_path"`
       EmbeddingsPath string `json:"embeddings_path"`
       ThresholdsPath string `json:"thresholds_path"`
   }

   // ThresholdConfig holds classification confidence thresholds.
   type ThresholdConfig struct {
       KeywordExactConfidence      float64 `json:"keyword_exact_confidence"`
       KeywordFuzzyConfidence      float64 `json:"keyword_fuzzy_confidence"`
       SemanticHighThreshold       float64 `json:"semantic_high_threshold"`
       SemanticMinGap              float64 `json:"semantic_min_gap"`
       SemanticAmbiguousThreshold  float64 `json:"semantic_ambiguous_threshold"`
       SemanticNoMatchThreshold    float64 `json:"semantic_no_match_threshold"`
       RerankerConfidenceFloor     float64 `json:"reranker_confidence_floor"`
   }

   // RateLimitConfig holds rate limiting settings.
   type RateLimitConfig struct {
       RequestsPerMinute int `json:"requests_per_minute"`
   }

   // LogConfig holds logging settings.
   type LogConfig struct {
       Level  string `json:"level"`
       Format string `json:"format"`
   }
   ```

2. **Implement the `Load()` function** that:
   - Attempts to load `.env` file via `godotenv.Load()` (non-fatal if missing — production uses real env vars)
   - Reads each environment variable with explicit defaults
   - Validates required fields (Azure endpoint, API keys)
   - Returns a populated `Config` or an error with a clear message about what's missing

   ```go
   func Load() (*Config, error) {
       // Best-effort .env loading
       _ = godotenv.Load()

       cfg := &Config{
           Server: ServerConfig{
               Port:            getEnvInt("KAIROS_PORT", 8080),
               ReadTimeout:     getEnvDuration("KAIROS_READ_TIMEOUT", 10*time.Second),
               WriteTimeout:    getEnvDuration("KAIROS_WRITE_TIMEOUT", 10*time.Second),
               ShutdownTimeout: getEnvDuration("KAIROS_SHUTDOWN_TIMEOUT", 15*time.Second),
               APIKey:          getEnvRequired("KAIROS_API_KEY"),
           },
           AzureAI: AzureAIConfig{
               Endpoint:            getEnvRequired("AZURE_AI_FOUNDRY_ENDPOINT"),
               APIKey:              getEnvRequired("AZURE_AI_FOUNDRY_API_KEY"),
               EmbeddingDeployment: getEnvStr("AZURE_AI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
               EmbeddingDimensions: getEnvInt("AZURE_AI_EMBEDDING_DIMENSIONS", 1536),
               RerankerDeployment:  getEnvStr("AZURE_AI_RERANKER_DEPLOYMENT", "gpt-4o-mini"),
               RerankerMaxTokens:   getEnvInt("AZURE_AI_RERANKER_MAX_TOKENS", 10),
               RerankerTemperature: getEnvFloat("AZURE_AI_RERANKER_TEMPERATURE", 0.0),
               RerankerTimeout:     getEnvDuration("AZURE_AI_RERANKER_TIMEOUT_MS", 2000*time.Millisecond),
           },
           Catalog: CatalogConfig{
               CatalogPath:    getEnvStr("KAIROS_CATALOG_PATH", "data/catalog.json"),
               EmbeddingsPath: getEnvStr("KAIROS_EMBEDDINGS_PATH", "data/embeddings.json"),
               ThresholdsPath: getEnvStr("KAIROS_THRESHOLDS_PATH", "data/thresholds.json"),
           },
           Threshold: ThresholdConfig{
               KeywordExactConfidence:     getEnvFloat("KEYWORD_EXACT_CONFIDENCE", 0.98),
               KeywordFuzzyConfidence:     getEnvFloat("KEYWORD_FUZZY_CONFIDENCE", 0.85),
               SemanticHighThreshold:      getEnvFloat("SEMANTIC_HIGH_THRESHOLD", 0.78),
               SemanticMinGap:             getEnvFloat("SEMANTIC_MIN_GAP", 0.08),
               SemanticAmbiguousThreshold: getEnvFloat("SEMANTIC_AMBIGUOUS_THRESHOLD", 0.65),
               SemanticNoMatchThreshold:   getEnvFloat("SEMANTIC_NO_MATCH_THRESHOLD", 0.65),
               RerankerConfidenceFloor:    getEnvFloat("RERANKER_CONFIDENCE_FLOOR", 0.70),
           },
           RateLimit: RateLimitConfig{
               RequestsPerMinute: getEnvInt("KAIROS_RATE_LIMIT_PER_MIN", 500),
           },
           Log: LogConfig{
               Level:  getEnvStr("KAIROS_LOG_LEVEL", "info"),
               Format: getEnvStr("KAIROS_LOG_FORMAT", "json"),
           },
       }

       if err := cfg.Validate(); err != nil {
           return nil, fmt.Errorf("config validation failed: %w", err)
       }

       return cfg, nil
   }
   ```

3. **Implement helper functions:** `getEnvStr`, `getEnvInt`, `getEnvFloat`, `getEnvDuration`, `getEnvRequired` — each reads `os.Getenv`, applies defaults, and parses the appropriate type.

4. **Implement `Validate()` method** on `Config` that checks:
   - `Server.Port` is between 1 and 65535
   - `Server.APIKey` is non-empty
   - `AzureAI.Endpoint` is a valid URL (starts with `https://`)
   - `AzureAI.APIKey` is non-empty
   - `AzureAI.EmbeddingDimensions` is > 0
   - All threshold values are between 0.0 and 1.0
   - `RateLimit.RequestsPerMinute` is > 0

5. **Implement `LoadThresholdsFromFile(path string) error`** method that reads `data/thresholds.json` and overrides the default threshold values, enabling hot-tuning without redeployment.

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/joho/godotenv v1.5+` — .env file loading (verify latest stable as of March 2026)

## Acceptance Criteria
1. `config.Load()` returns a fully populated `Config` struct when all required env vars are set
2. `config.Load()` returns a descriptive error when any required env var is missing
3. Default values are correctly applied for optional env vars
4. Validation rejects invalid port numbers, empty API keys, malformed URLs, and out-of-range thresholds
5. `LoadThresholdsFromFile` correctly overrides threshold values from a JSON file
6. Secrets (`APIKey` fields) are tagged `json:"-"` and never appear in serialized output
7. Unit test coverage ≥ 90% for the config package

## Testing Requirements
- **Unit Tests:** Test `Load()` with various combinations of set/unset env vars using `t.Setenv()`. Test `Validate()` with boundary values. Test each `getEnv*` helper independently. Test `LoadThresholdsFromFile` with valid and invalid JSON.
- **Integration Tests:** None needed — this is a pure in-process module
- **Manual Verification:** Set env vars in shell, run binary, verify config values in log output

## Files to Create/Modify
- `internal/config/config.go` — (create) Configuration types, loader, validation
- `internal/config/config_test.go` — (create) Comprehensive unit tests
- `go.mod` — (modify) Add `github.com/joho/godotenv` dependency
- `go.sum` — (modify) Updated automatically

## Risks & Edge Cases
- Environment variables with whitespace or special characters — `os.Getenv` returns raw values, which should be trimmed for string fields.
- Duration parsing: the env var `AZURE_AI_RERANKER_TIMEOUT_MS` is in milliseconds but the Config field is `time.Duration`. The helper must convert correctly.
- `.env` file loading is best-effort; the service must work without it (production environments set env vars directly).
- If `thresholds.json` doesn't exist, `LoadThresholdsFromFile` should return a descriptive error but the service should still start with defaults.

## Notes
- The `Validate()` method should collect all errors (not fail on first) and return them as a combined error message, making it easier for operators to fix multiple misconfigurations at once.
- Consider adding a `String()` or `Redacted()` method that prints config for debugging with secrets masked.
