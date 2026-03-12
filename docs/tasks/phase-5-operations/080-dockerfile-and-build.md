# TASK-080: Production Dockerfile and Multi-Stage Build

## Metadata
- **Phase:** 5
- **Module:** infra
- **Priority:** P0-critical
- **Estimated Effort:** 1-2 days
- **Owner Role:** DevOps engineer / Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001, TASK-004]
- **Blocks:** [TASK-103]
- **Related:** [TASK-009, TASK-008]

## Objective
Create a production-ready multi-stage Dockerfile that builds the Go binary in a builder stage and runs it in a minimal Alpine image. The final image should be small (<30MB), run as a non-root user, and include only the binary and data files.

## Design Reference
- See Design Doc §7 Deployment & Operations
- See Design Doc §7.1 Container Image

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (Go module and Makefile)
- TASK-004 complete (health check endpoint for container probes)

### Implementation Details

1. **Create `Dockerfile`:**

   ```dockerfile
   # Stage 1: Build
   FROM golang:1.22-alpine AS builder

   RUN apk add --no-cache git make

   WORKDIR /build

   COPY go.mod go.sum ./
   RUN go mod download

   COPY . .

   ARG VERSION=dev
   ARG GIT_COMMIT=unknown
   ARG BUILD_TIME=unknown

   RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
       -ldflags "-s -w \
           -X github.com/kaseya/kairos/internal/api.Version=${VERSION} \
           -X github.com/kaseya/kairos/internal/api.GitCommit=${GIT_COMMIT} \
           -X github.com/kaseya/kairos/internal/api.BuildTime=${BUILD_TIME}" \
       -o /build/kairos ./cmd/server

   # Stage 2: Runtime
   FROM alpine:3.20

   RUN apk add --no-cache ca-certificates tzdata && \
       addgroup -g 1000 kairos && \
       adduser -u 1000 -G kairos -s /bin/sh -D kairos

   WORKDIR /app

   COPY --from=builder /build/kairos .
   COPY --from=builder /build/data/ ./data/

   RUN chown -R kairos:kairos /app

   USER kairos

   EXPOSE 8080

   HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
       CMD wget -qO- http://localhost:8080/healthz || exit 1

   ENTRYPOINT ["/app/kairos"]
   ```

2. **Update Makefile** with Docker build targets:
   ```makefile
   docker-build:
   	docker build \
   		--build-arg VERSION=$(VERSION) \
   		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
   		--build-arg BUILD_TIME=$(BUILD_TIME) \
   		-t kairos:$(VERSION) \
   		-t kairos:latest \
   		.

   docker-push:
   	docker push kairos:$(VERSION)
   	docker push kairos:latest
   ```

3. **Create `.dockerignore`:**
   ```
   .git
   .github
   .env
   .env.local
   .idea
   .vscode
   tmp
   bin
   coverage.*
   docs
   scripts
   *.md
   Dockerfile.dev
   .air.toml
   docker-compose.yml
   ```

### Tech Stack & Dependencies
- Docker 24+ with multi-stage build support
- `golang:1.22-alpine` builder image
- `alpine:3.20` runtime image (verify latest stable as of March 2026)

## Acceptance Criteria
1. `docker build .` completes successfully
2. Final image size is under 30MB
3. Container runs as non-root user (`kairos`, UID 1000)
4. Health check probe works (`/healthz`)
5. Binary is statically linked (`CGO_ENABLED=0`)
6. Version, git commit, and build time are embedded via ldflags
7. Data files are included in the image
8. `.dockerignore` excludes development files, docs, and secrets

## Testing Requirements
- **Unit Tests:** None — infrastructure
- **Integration Tests:** Build image, run container, verify health check responds, verify version endpoint shows correct build metadata.
- **Manual Verification:** `docker build -t kairos:test . && docker run --rm -p 8080:8080 --env-file .env kairos:test`

## Files to Create/Modify
- `Dockerfile` — (create) Production multi-stage Dockerfile
- `.dockerignore` — (create) Docker build context exclusions
- `Makefile` — (modify) Add docker-build and docker-push targets

## Risks & Edge Cases
- Alpine's `wget` is BusyBox version — healthcheck uses `wget -qO-` instead of `curl`. If issues arise, install `curl` in the runtime image.
- `ca-certificates` is required for HTTPS calls to Azure AI Foundry. Without it, TLS fails.
- Architecture: the Dockerfile builds for `linux/amd64`. For multi-arch support (ARM), add buildx support.

## Notes
- The `data/` directory (catalog, embeddings, thresholds) is copied into the image at build time. For dynamic data updates without rebuilding, mount as a volume or use the hot-reload endpoint (TASK-083).
