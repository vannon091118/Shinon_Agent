# Ops Playbooks

## CI red: `verify:backend` fails

1. Reproduce locally with `npm run verify:backend`.
2. Identify the failing stage from output (`contract-gate`, `replay-gate`, `baseline-integrity`, unit or integration specs).
3. Fix the failing contract/replay assumption first; do not relax gates to force green CI.

## Replay gate fail / hash drift

1. Run `npm run test:determinism` and `npm run test:baseline-integrity`.
2. Compare payload ordering and sequence values in replay hash inputs; nondeterministic key order or sequence drift are common causes.
3. Keep replay hash inputs deterministic and ensure sequence progression remains strictly monotonic.

## `.next` locked

1. Run `npm run stop:local` to stop listeners and trigger automated `.next` cleanup.
2. If cleanup warns after retries, close all Next.js terminals/Node processes.
3. Run `npm run stop:local` again; if needed remove `frontend/.next` manually after processes are closed.

## SQLite path / migration issues

1. For explicit SQLite mode, run backend with `SHINON_MEMORY_SQLITE=1` and inspect startup error details.
2. Confirm parent directory permissions for resolved DB path and that `node:sqlite` is available in current Node runtime.
3. Check `PRAGMA user_version`; unsupported higher versions must be migrated explicitly before startup can continue.

