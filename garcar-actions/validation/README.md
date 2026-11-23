# Local validation — 2026-11-02

Result: passed on Linux with Python 3.12.14. Run from the hub's `garcar-actions/` directory:

```bash
python scripts/ci.py --report-dir validation
```

The checked-in `source-sha256.json` identifies the code, profiles, scripts, and documentation for this validation snapshot. Reports contain no service credentials or persistent job state.

| Check | Observed result | Evidence |
|---|---|---|
| Python compilation | Passed | `local-ci.txt` |
| Unit/integration regressions | 32 passed | `local-ci.txt` |
| Separate API and worker processes | Passed; 4 fixture jobs had expected outcomes | `local-smoke.json` |
| Authentication and invalid requests | 8 checks passed | `local-smoke.json` |
| Duplicate HTTP submissions | 4 retried requests reused their job IDs | `local-smoke.json` |
| Canary audit integrity | Valid, 12 entries | `local-smoke.json` |
| Pinned native hub structure job | Succeeded, exit code 0 | `hub-canary.json` |
| Native job audit integrity | Valid, 3 entries | `hub-canary.json` |
| Hub workflow census | 53 files with SHA-256 | `hub-inventory.json` |

The regression suite covers credential exclusion, concurrent request idempotency, queue quota, old-schema upgrade preservation, audit tampering, source changes, path redirection, empty test suites, test failures, output flood limits, timeout cleanup, same-group descendants, interrupted-job closure, and scanner privilege/symlink handling.

The structure job is a documented port with stricter JSON error handling. It does not establish exact parity with the entire GitHub workflow. Inventory counts are declarations from repository files. The larger repository census remains partial, three hub CI jobs remain untranslated, and GitHub triggers are unchanged. Docker/Termux target-host execution, hosted CI success, per-job OS isolation, and unattended production activation are not established by these local results.
