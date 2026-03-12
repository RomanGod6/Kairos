# TASK-001: Repository Initialization and Go Module Setup

## Metadata
- **Phase:** 1
- **Module:** cmd
- **Priority:** P0-critical
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** None
- **Blocks:** [TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011]
- **Related:** None

## Objective
Initialize the Go module, create the canonical directory structure, set up the Makefile with common targets, and configure essential project files (.gitignore, .env.example, .editorconfig). This is the foundational task — every subsequent task depends on a valid Go module and directory layout.

## Design Reference
- See Design Doc §2 Architecture Overview (project structure diagram)
- See Design Doc §1 Introduction (technology choices: Go microservice)

## Technical Requirements

### Inputs / Prerequisites
- Go 1.22+ installed
- Empty Git repository initialized

### Implementation Details

1. **Initialize Go module:**
   ```bash
   go mod init github.com/kaseya/kairos
   ```

2. **Create the full directory tree:**
   ```
   cmd/server/
   internal/api/
   internal/catalog/
   internal/classify/
   internal/tier1/
   internal/tier2/
   internal/tier3/
   internal/azureai/
   internal/preprocess/
   internal/config/
   pkg/client/
   data/
   scripts/extract-catalog/
   scripts/eval/testdata/
   docs/
   ```

3. **Create placeholder `main.go`:**
   ```go
   // cmd/server/main.go
   package main

   import (
       "fmt"
       "os"
   )

   func main() {
       fmt.Println("Kairos server starting...")
       os.Exit(0)
   }
   ```

4. **Create `.gitignore`:**
   ```
   # Binaries
   /bin/
   /kairos
   *.exe

   # Environment
   .env
   .env.local

   # IDE
   .idea/
   .vscode/
   *.swp
   *.swo

   # OS
   .DS_Store
   Thumbs.db

   # Test
   coverage.out
   coverage.html

   # Vendor (if used)
   /vendor/
   ```

5. **Create `.env.example`:**
   ```env
   # Kairos Configuration
   KAIROS_PORT=8080
   KAIROS_LOG_LEVEL=info
   KAIROS_LOG_FORMAT=json
   KAIROS_API_KEY=changeme

   # Azure AI Foundry — Base config
   AZURE_AI_FOUNDRY_ENDPOINT=https://<resource>.services.ai.azure.com
   AZURE_AI_FOUNDRY_API_KEY=<key>

   # Embedding model deployment (Tier 2)
   AZURE_AI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
   AZURE_AI_EMBEDDING_DIMENSIONS=1536

   # Chat completion model deployment (Tier 3 reranker)
   AZURE_AI_RERANKER_DEPLOYMENT=gpt-4o-mini
   AZURE_AI_RERANKER_MAX_TOKENS=10
   AZURE_AI_RERANKER_TEMPERATURE=0
   AZURE_AI_RERANKER_TIMEOUT_MS=2000

   # Rate limiting
   KAIROS_RATE_LIMIT_PER_MIN=500

   # Catalog
   KAIROS_CATALOG_PATH=data/catalog.json
   KAIROS_EMBEDDINGS_PATH=data/embeddings.json
   KAIROS_THRESHOLDS_PATH=data/thresholds.json
   ```

6. **Create `.editorconfig`:**
   ```ini
   root = true

   [*]
   charset = utf-8
   end_of_line = lf
   insert_final_newline = true
   trim_trailing_whitespace = true
   indent_style = tab
   indent_size = 4

   [*.md]
   indent_style = space
   indent_size = 2

   [*.{json,yaml,yml}]
   indent_style = space
   indent_size = 2
   ```

7. **Create `Makefile`:**
   ```makefile
   .PHONY: build run test lint fmt vet clean docker-build docker-run

   BINARY_NAME=kairos
   BUILD_DIR=./bin
   MAIN_PKG=./cmd/server

   build:
   	go build -o $(BUILD_DIR)/$(BINARY_NAME) $(MAIN_PKG)

   run: build
   	$(BUILD_DIR)/$(BINARY_NAME)

   test:
   	go test -race -coverprofile=coverage.out ./...

   test-coverage: test
   	go tool cover -html=coverage.out -o coverage.html

   lint:
   	golangci-lint run ./...

   fmt:
   	gofmt -s -w .

   vet:
   	go vet ./...

   clean:
   	rm -rf $(BUILD_DIR) coverage.out coverage.html

   docker-build:
   	docker build -t kairos:latest .

   docker-run:
   	docker run --env-file .env -p 8080:8080 kairos:latest
   ```

8. **Verify the project compiles:** `go build ./...`

### Tech Stack & Dependencies
- `go 1.22+` (latest stable as of March 2026; verify with `go version`)
- GNU Make 4.x

## Acceptance Criteria
1. `go build ./cmd/server` compiles without errors
2. Running the binary prints "Kairos server starting..." and exits cleanly
3. All directories in the project structure exist with appropriate `.gitkeep` or source files
4. `.gitignore` prevents committing binaries, `.env`, IDE files, and coverage artifacts
5. `.env.example` documents all expected environment variables with placeholder values
6. `make build` produces a binary at `./bin/kairos`
7. `make test` runs (even if no tests exist yet — should exit 0)
8. `go mod tidy` produces no changes (module is clean)

## Testing Requirements
- **Unit Tests:** None for this task — it's project scaffolding
- **Integration Tests:** None
- **Manual Verification:** Run `go build ./cmd/server`, execute the binary, confirm output. Run `make build`, `make test`, `make clean` and verify each target works.

## Files to Create/Modify
- `go.mod` — (create) Go module definition
- `cmd/server/main.go` — (create) Entry point placeholder
- `.gitignore` — (create) Git ignore rules
- `.env.example` — (create) Environment variable documentation
- `.editorconfig` — (create) Editor configuration
- `Makefile` — (create) Build automation targets

## Risks & Edge Cases
- Go version mismatch: ensure the CI and developer machines are on Go 1.22+. The `go.mod` `go` directive should enforce this.
- Make may not be installed on Windows developer machines — document that WSL2 or a Unix-like environment is required for local development.

## Notes
- The module path `github.com/kaseya/kairos` is the canonical import path. If the actual GitHub org differs, update before the first public push.
- All subsequent tasks assume this directory structure exists exactly as specified.
