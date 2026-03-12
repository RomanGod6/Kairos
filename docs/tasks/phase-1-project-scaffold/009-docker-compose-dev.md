# TASK-009: Docker Compose Local Development Environment

## Metadata
- **Phase:** 1
- **Module:** infra
- **Priority:** P2-medium
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer / DevOps engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001, TASK-002, TASK-003]
- **Blocks:** [TASK-020]
- **Related:** [TASK-080]

## Objective
Create a `docker-compose.yml` for local development that runs the Kairos service alongside a Meilisearch instance. This enables developers to test catalog extraction and the full service stack without external infrastructure.

## Design Reference
- See Design Doc §7.2 Local Development Environment
- See Design Doc §3.2 Meilisearch (catalog extraction source)

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (HTTP server runs)

### Implementation Details

1. **Create `docker-compose.yml`:**

   ```yaml
   version: "3.9"

   services:
     kairos:
       build:
         context: .
         dockerfile: Dockerfile.dev
       ports:
         - "8080:8080"
       env_file:
         - .env
       volumes:
         - ./data:/app/data
       depends_on:
         meilisearch:
           condition: service_healthy
       restart: unless-stopped

     meilisearch:
       image: getmeili/meilisearch:v1.11
       ports:
         - "7700:7700"
       environment:
         MEILI_ENV: development
         MEILI_MASTER_KEY: dev-master-key
       volumes:
         - meilisearch-data:/meili_data
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:7700/health"]
         interval: 10s
         timeout: 5s
         retries: 5

   volumes:
     meilisearch-data:
   ```

2. **Create `Dockerfile.dev`** (development-only Dockerfile with hot reload support):

   ```dockerfile
   FROM golang:1.22-alpine

   WORKDIR /app

   # Install air for hot reload
   RUN go install github.com/air-verse/air@latest

   COPY go.mod go.sum ./
   RUN go mod download

   COPY . .

   EXPOSE 8080

   CMD ["air", "-c", ".air.toml"]
   ```

3. **Create `.air.toml`** (hot reload configuration):

   ```toml
   root = "."
   tmp_dir = "tmp"

   [build]
   cmd = "go build -o ./tmp/kairos ./cmd/server"
   bin = "./tmp/kairos"
   include_ext = ["go", "json"]
   exclude_dir = ["tmp", "vendor", "data", "docs", "scripts"]
   delay = 1000

   [log]
   time = false

   [misc]
   clean_on_exit = true
   ```

### Tech Stack & Dependencies
- Docker 24+ and Docker Compose v2
- `getmeili/meilisearch:v1.11` (verify latest stable as of March 2026)
- `github.com/air-verse/air` — hot reload for Go (development only)

## Acceptance Criteria
1. `docker compose up` starts both Kairos and Meilisearch containers
2. Kairos waits for Meilisearch to be healthy before starting
3. Meilisearch is accessible at `http://localhost:7700` with the dev master key
4. Kairos is accessible at `http://localhost:8080`
5. Code changes in Go files trigger automatic rebuild via air
6. `docker compose down` cleanly stops all services
7. Meilisearch data persists across restarts via named volume

## Testing Requirements
- **Unit Tests:** None — infrastructure configuration
- **Integration Tests:** None
- **Manual Verification:** Run `docker compose up`, verify both services respond to health checks, edit a Go file, verify hot reload triggers

## Files to Create/Modify
- `docker-compose.yml` — (create) Multi-service local development stack
- `Dockerfile.dev` — (create) Development Dockerfile with hot reload
- `.air.toml` — (create) Air hot reload configuration

## Risks & Edge Cases
- Port conflicts: 8080 and 7700 may be in use on developer machines. Document port override via environment variables.
- Meilisearch data volume can grow large over time — document `docker volume prune` for cleanup.
- The `Dockerfile.dev` is NOT for production — it includes dev tooling and runs as root. The production Dockerfile (TASK-080) is separate.

## Notes
- The `.env` file must exist locally for `docker compose up` to work. Developers should copy `.env.example` to `.env` and fill in values.
- Meilisearch is only needed for catalog extraction (Phase 2). The Kairos service itself doesn't connect to Meilisearch at runtime.
