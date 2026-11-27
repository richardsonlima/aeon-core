# 001. Rewrite the package for v0.5.0

- Status: accepted
- Date: 2026-11-27

## Context

v0.4.0 is a general assistant framework with 17 hard dependencies, no tests and no console script. The v0.5.0 brief defines a different product: a small, dependency-free action gate with chaos injection and a hash-chained audit log.

## Decision

Replace the contents of `src/aeon/` with the v0.5.0 design. Remove the legacy top-level docs and example folders. The legacy code remains at tag `v0.4.0-ULTRA`.

## Consequences

- Users of `aeon.Agent` and the v0.4 subpackages must pin `aeon-core==0.4.0`. This is stated in `CHANGELOG.md` under "Removed".
- The core install has no third-party dependencies. FastAPI, uvicorn and provider SDKs move to extras.
