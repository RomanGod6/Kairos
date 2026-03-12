# TASK-065: API Versioning and Documentation

## Metadata
- **Phase:** 4
- **Module:** api
- **Priority:** P3-low
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-060]
- **Blocks:** None
- **Related:** [TASK-063, TASK-064]

## Objective
Add a version info endpoint (`GET /version`) that returns the service version, git commit hash, and build time. Establish the `/v1/` prefix convention and document the versioning strategy for future API evolution.

## Design Reference
- See Design Doc §5 API Contract (versioning strategy)
- See Design Doc §7 Deployment (build metadata)

## Technical Requirements

### Inputs / Prerequisites
- TASK-060 complete (API endpoints functional)

### Implementation Details

1. **Create version handler in `internal/api/handler.go`:**

   ```go
   // Build-time variables set via ldflags.
   var (
       Version   = "dev"
       GitCommit = "unknown"
       BuildTime = "unknown"
   )

   type VersionResponse struct {
       Version   string `json:"version"`
       GitCommit string `json:"git_commit"`
       BuildTime string `json:"build_time"`
   }

   func VersionHandler() http.HandlerFunc {
       return func(w http.ResponseWriter, r *http.Request) {
           WriteJSON(w, http.StatusOK, VersionResponse{
               Version:   Version,
               GitCommit: GitCommit,
               BuildTime: BuildTime,
           })
       }
   }
   ```

2. **Update Makefile** to pass ldflags at build time:
   ```makefile
   VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
   GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
   BUILD_TIME ?= $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')
   LDFLAGS := -X github.com/kaseya/kairos/internal/api.Version=$(VERSION) \
              -X github.com/kaseya/kairos/internal/api.GitCommit=$(GIT_COMMIT) \
              -X github.com/kaseya/kairos/internal/api.BuildTime=$(BUILD_TIME)

   build:
   	go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_NAME) $(MAIN_PKG)
   ```

3. **Register route:** `r.Get("/version", VersionHandler())` (unauthenticated)

### Tech Stack & Dependencies
- `go 1.22+`

## Acceptance Criteria
1. `GET /version` returns HTTP 200 with version, git commit, and build time
2. Build-time ldflags populate the version fields correctly
3. Default values ("dev", "unknown") are returned when not built with ldflags
4. Endpoint is unauthenticated

## Testing Requirements
- **Unit Tests:** Test VersionHandler returns expected default values.
- **Integration Tests:** None
- **Manual Verification:** `make build && curl http://localhost:8080/version`

## Files to Create/Modify
- `internal/api/handler.go` — (modify) Add VersionHandler
- `internal/api/routes.go` — (modify) Register /version route
- `Makefile` — (modify) Add ldflags for version info

## Risks & Edge Cases
- None significant.

## Notes
- This endpoint is useful for deployment verification and debugging.
