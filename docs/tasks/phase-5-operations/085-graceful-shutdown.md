# TASK-085: Graceful Shutdown Enhancement

## Metadata
- **Phase:** 5
- **Module:** cmd
- **Priority:** P1-high
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-003, TASK-081]
- **Blocks:** None
- **Related:** [TASK-080]

## Objective
Enhance the graceful shutdown flow to ensure all in-flight requests complete, metrics are flushed, and the readiness probe transitions to unhealthy before the server stops accepting new connections. This prevents request loss during deployments.

## Design Reference
- See Design Doc §7.5 Graceful Shutdown
- See Design Doc §7 Deployment (rolling update strategy)

## Technical Requirements

### Inputs / Prerequisites
- TASK-003 complete (basic graceful shutdown exists)
- TASK-081 complete (metrics to flush)

### Implementation Details

1. **Update shutdown sequence in `cmd/server/main.go`:**

   ```go
   // Shutdown sequence:
   // 1. Set readiness to false (stop receiving new traffic from LB)
   // 2. Wait brief drain period for LB to stop sending requests
   // 3. Stop accepting new connections
   // 4. Wait for in-flight requests to complete
   // 5. Flush metrics
   // 6. Exit

   readiness.SetReady(false)
   log.Info().Msg("readiness set to false, draining connections")

   // Brief drain period for load balancer to detect unhealthy readiness
   time.Sleep(5 * time.Second)

   ctx, cancel := context.WithTimeout(context.Background(), cfg.Server.ShutdownTimeout)
   defer cancel()

   if err := srv.Shutdown(ctx); err != nil {
       log.Error().Err(err).Msg("server forced shutdown")
   }

   log.Info().Msg("server stopped gracefully")
   ```

2. **Update readiness handler** to check the `ReadinessState` (connect to TASK-004).

### Tech Stack & Dependencies
- `go 1.22+`

## Acceptance Criteria
1. Readiness probe returns 503 immediately after shutdown signal
2. In-flight requests complete within the shutdown timeout
3. 5-second drain period allows load balancer to stop routing traffic
4. Server exits cleanly with status code 0 after successful shutdown
5. Forced shutdown (timeout exceeded) exits with non-zero status

## Testing Requirements
- **Unit Tests:** Test readiness state transitions.
- **Integration Tests:** Send a long-running request, trigger shutdown, verify request completes.
- **Manual Verification:** Deploy, trigger SIGTERM, verify clean shutdown in logs.

## Files to Create/Modify
- `cmd/server/main.go` — (modify) Enhanced shutdown sequence
- `internal/api/handler.go` — (modify) Wire ReadinessState into readiness handler

## Risks & Edge Cases
- The 5-second drain period adds to total shutdown time. Kubernetes `terminationGracePeriodSeconds` must be greater than `ShutdownTimeout + 5s`.
- If a request is stuck in an Azure AI call that exceeds the shutdown timeout, it will be forcibly terminated.

## Notes
- This is critical for zero-downtime deployments in Kubernetes.
