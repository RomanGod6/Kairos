# TASK-003: HTTP Server Skeleton with Graceful Shutdown

## Metadata
- **Phase:** 1
- **Module:** cmd
- **Priority:** P0-critical
- **Estimated Effort:** 1-2 days
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001, TASK-002]
- **Blocks:** [TASK-004, TASK-005, TASK-060, TASK-061, TASK-062]
- **Related:** None

## Objective
Build the HTTP server in `cmd/server/main.go` using `chi` router with graceful shutdown on SIGINT/SIGTERM. This is the process skeleton that all API endpoints and middleware will plug into.

## Design Reference
- See Design Doc §2 Architecture Overview (HTTP server layer)
- See Design Doc §5 API Contract (endpoint routing)

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (project structure)
- TASK-002 complete (config loading)

### Implementation Details

1. **Update `cmd/server/main.go`:**

   ```go
   package main

   import (
       "context"
       "fmt"
       "net/http"
       "os"
       "os/signal"
       "syscall"
       "time"

       "github.com/kaseya/kairos/internal/api"
       "github.com/kaseya/kairos/internal/config"
       "github.com/rs/zerolog"
       "github.com/rs/zerolog/log"
   )

   func main() {
       // Load configuration
       cfg, err := config.Load()
       if err != nil {
           fmt.Fprintf(os.Stderr, "failed to load config: %v\n", err)
           os.Exit(1)
       }

       // Initialize logger
       initLogger(cfg.Log)

       log.Info().
           Int("port", cfg.Server.Port).
           Str("log_level", cfg.Log.Level).
           Msg("starting Kairos server")

       // Build router
       router := api.NewRouter(cfg)

       // Create HTTP server
       srv := &http.Server{
           Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
           Handler:      router,
           ReadTimeout:  cfg.Server.ReadTimeout,
           WriteTimeout: cfg.Server.WriteTimeout,
       }

       // Start server in goroutine
       errCh := make(chan error, 1)
       go func() {
           if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
               errCh <- err
           }
       }()

       // Wait for interrupt signal
       quit := make(chan os.Signal, 1)
       signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

       select {
       case sig := <-quit:
           log.Info().Str("signal", sig.String()).Msg("shutting down server")
       case err := <-errCh:
           log.Fatal().Err(err).Msg("server error")
       }

       // Graceful shutdown
       ctx, cancel := context.WithTimeout(context.Background(), cfg.Server.ShutdownTimeout)
       defer cancel()

       if err := srv.Shutdown(ctx); err != nil {
           log.Fatal().Err(err).Msg("server forced shutdown")
       }

       log.Info().Msg("server stopped gracefully")
   }

   func initLogger(cfg config.LogConfig) {
       level, err := zerolog.ParseLevel(cfg.Level)
       if err != nil {
           level = zerolog.InfoLevel
       }
       zerolog.SetGlobalLevel(level)

       if cfg.Format == "console" {
           log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stdout})
       }
       // Default is JSON output (zerolog default)
   }
   ```

2. **Create `internal/api/routes.go`:**

   ```go
   package api

   import (
       "github.com/go-chi/chi/v5"
       "github.com/go-chi/chi/v5/middleware"
       "github.com/kaseya/kairos/internal/config"
   )

   // NewRouter creates and configures the chi router with all middleware and routes.
   func NewRouter(cfg *config.Config) *chi.Mux {
       r := chi.NewRouter()

       // Global middleware
       r.Use(middleware.RequestID)
       r.Use(middleware.RealIP)
       r.Use(middleware.Recoverer)
       r.Use(middleware.Timeout(cfg.Server.WriteTimeout))

       // Health check (unauthenticated)
       r.Get("/healthz", HealthCheckHandler())
       r.Get("/readyz", ReadinessCheckHandler())

       // API v1 routes (authenticated)
       r.Route("/v1", func(r chi.Router) {
           // Auth and rate limiting middleware will be added in TASK-061 and TASK-062
           // r.Use(AuthMiddleware(cfg.Server.APIKey))
           // r.Use(RateLimitMiddleware(cfg.RateLimit))

           // Classification endpoint will be added in TASK-060
           // r.Post("/classify", ClassifyHandler(...))
       })

       return r
   }
   ```

3. **Create `internal/api/handler.go`** with placeholder for health handlers (full implementation in TASK-004).

### Tech Stack & Dependencies
- `go 1.22+`
- `github.com/go-chi/chi/v5 v5.1+` — HTTP router (verify latest stable as of March 2026)
- `github.com/rs/zerolog v1.33+` — Structured JSON logging (verify latest stable)

## Acceptance Criteria
1. `go build ./cmd/server` compiles without errors
2. The server starts, listens on the configured port, and logs a startup message
3. The server responds to HTTP requests (even if routes return 404 for unregistered paths)
4. Sending SIGINT (Ctrl+C) triggers graceful shutdown — the server stops accepting new connections, waits for in-flight requests, and exits cleanly
5. Sending SIGTERM triggers the same graceful shutdown behavior
6. Server respects `ReadTimeout`, `WriteTimeout`, and `ShutdownTimeout` from config
7. If the port is already in use, the server logs a fatal error and exits with code 1

## Testing Requirements
- **Unit Tests:** Test `initLogger` with different log config values. Test that `NewRouter` returns a valid `chi.Mux` with expected route patterns.
- **Integration Tests:** Start the server in a test goroutine, send an HTTP request, verify response, send SIGINT, verify clean shutdown.
- **Manual Verification:** Run `make run`, curl `http://localhost:8080/healthz` (should return 404 until TASK-004), press Ctrl+C, confirm graceful shutdown log.

## Files to Create/Modify
- `cmd/server/main.go` — (modify) Full server implementation with graceful shutdown
- `internal/api/routes.go` — (create) Chi router setup with middleware and route registration
- `internal/api/handler.go` — (create) Placeholder handler file
- `go.mod` — (modify) Add chi and zerolog dependencies
- `go.sum` — (modify) Updated automatically

## Risks & Edge Cases
- Port conflict on startup: the server should log a clear error and exit (not hang).
- Long-running requests during shutdown: the shutdown timeout must be respected. If requests exceed the timeout, they are forcibly terminated.
- Signal handling: only register SIGINT and SIGTERM. Do not catch SIGKILL (it's uncatchable anyway).

## Notes
- The `middleware.Timeout` wraps each request with a context deadline equal to `WriteTimeout`. This prevents individual requests from hanging indefinitely.
- The `middleware.Recoverer` catches panics and returns 500 instead of crashing the process.
- Logging middleware (structured request logging with zerolog) will be added in TASK-082.
