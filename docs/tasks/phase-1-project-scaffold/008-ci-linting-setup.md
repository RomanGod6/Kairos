# TASK-008: CI Linting and Code Quality Configuration

## Metadata
- **Phase:** 1
- **Module:** infra
- **Priority:** P2-medium
- **Estimated Effort:** 4-8 hours
- **Owner Role:** Go backend engineer

## Status & Dependencies
- **Status:** planned
- **Blocked By:** [TASK-001, TASK-002]
- **Blocks:** None
- **Related:** [TASK-080]

## Objective
Configure `golangci-lint` with a project-specific ruleset and create a GitHub Actions CI workflow that runs linting, tests, and build verification on every push and pull request. Catch code quality issues early and enforce consistent standards.

## Design Reference
- See Design Doc §7.1 CI/CD Pipeline

## Technical Requirements

### Inputs / Prerequisites
- TASK-001 complete (Go module, Makefile)
- TASK-002 complete (at least one package to lint)

### Implementation Details

1. **Create `.golangci.yml`:**

   ```yaml
   run:
     timeout: 5m
     go: "1.22"

   linters:
     enable:
       - errcheck
       - govet
       - staticcheck
       - unused
       - gosimple
       - ineffassign
       - typecheck
       - bodyclose
       - gocritic
       - gofmt
       - goimports
       - misspell
       - prealloc
       - revive
       - unconvert
       - unparam
     disable:
       - depguard

   linters-settings:
     govet:
       check-shadowing: true
     revive:
       rules:
         - name: exported
           disabled: true
     gocritic:
       enabled-tags:
         - diagnostic
         - style
         - performance
     misspell:
       locale: US

   issues:
     max-issues-per-linter: 0
     max-same-issues: 0
     exclude-rules:
       - path: _test\.go
         linters:
           - errcheck
           - gocritic
   ```

2. **Create `.github/workflows/ci.yml`:**

   ```yaml
   name: CI

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-go@v5
           with:
             go-version: "1.22"
         - name: golangci-lint
           uses: golangci/golangci-lint-action@v6
           with:
             version: latest

     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-go@v5
           with:
             go-version: "1.22"
         - name: Run tests
           run: make test
         - name: Upload coverage
           uses: actions/upload-artifact@v4
           with:
             name: coverage
             path: coverage.out

     build:
       runs-on: ubuntu-latest
       needs: [lint, test]
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-go@v5
           with:
             go-version: "1.22"
         - name: Build
           run: make build
   ```

### Tech Stack & Dependencies
- `golangci-lint v1.61+` (verify latest stable as of March 2026)
- GitHub Actions with `actions/checkout@v4`, `actions/setup-go@v5`, `golangci/golangci-lint-action@v6`

## Acceptance Criteria
1. `make lint` runs `golangci-lint` with the project config and passes on clean code
2. The CI workflow triggers on push to `main` and on all PRs
3. CI runs lint, test, and build stages — build only runs if lint and test pass
4. Linting failures block the build stage
5. Test coverage report is uploaded as a CI artifact

## Testing Requirements
- **Unit Tests:** None — this is CI infrastructure
- **Integration Tests:** None
- **Manual Verification:** Push a branch with a deliberate lint error, verify CI catches it. Push a clean branch, verify all stages pass.

## Files to Create/Modify
- `.golangci.yml` — (create) Linter configuration
- `.github/workflows/ci.yml` — (create) CI pipeline definition

## Risks & Edge Cases
- `golangci-lint` version pinning: the CI action uses `version: latest` which could introduce new lint failures after a linter update. Consider pinning to a specific version if stability is critical.
- Test stage may fail if no test files exist yet — ensure `make test` exits 0 when there are no tests (Go's default behavior with `./...` is correct: "no test files" is not an error).

## Notes
- Additional CI stages (Docker build, integration tests, deployment) will be added in later phases.
- Consider adding a `make ci` target that runs all CI checks locally for developer convenience.
