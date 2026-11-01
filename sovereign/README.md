# Garcar Sovereign Control Plane (Termux MVP)

This branch introduces a local-first deployment controller for Garcar. It does not invoke GitHub Actions, Railway, Vercel, Render, AWS, or another hosted deployment platform.

## Operating boundary

- Runs on the Android device in Termux using Python 3.
- Builds and tests local repository working copies.
- Stores release snapshots, logs, state, and a SHA-256 hash-chained audit ledger under `$HOME/.garcar-sovereign` by default.
- Application health probes use loopback URLs.
- No public ingress, DNS, TLS, cloud provisioning, payment execution, or remote secret mutation is performed.
- The controller inherits only explicitly allow-listed environment variables from the operator's shell. Secret values are never written into the manifest or deployment database.

This is a single-device development/canary controller. It is not an always-on production host: Android may suspend processes, and the controller does not configure a firewall, TLS, public ingress, or durable off-device backups.

## Install in Termux

```bash
pkg update
pkg install python git
mkdir -p ~/garcar-sovereign
# Copy sovereign/garcar.py and the example manifests into this directory.
python garcar.py init
python garcar.py --help
```

No pip packages are required.

## Local CI

Create `garcar.ci.json` in a repository:

```json
{
  "steps": [
    ["python", "-m", "unittest", "discover", "-v"],
    ["python", "-m", "compileall", "-q", "."]
  ]
}
```

Run:

```bash
python ~/garcar-sovereign/garcar.py ci /path/to/repository
```

Every step is an argument array and executes with `shell=False`. Shell strings, pipes, redirects, and command interpolation are intentionally unsupported.

## Application deployment manifest

Copy `garcar.deploy.example.json` to the application root as `garcar.deploy.json`, then set real start/build argument arrays. Do not put secret values in this file.

```json
{
  "name": "example-api",
  "build": [],
  "start": ["python", "app.py"],
  "port": 18080,
  "canary_port": 18081,
  "health": {"path": "/health"},
  "env_passthrough": ["APP_MODE"]
}
```

The controller injects `PORT`, `HOST=127.0.0.1`, `BIND_HOST=127.0.0.1`, and `GARCAR_BIND_HOST=127.0.0.1`. Applications must honor the loopback binding contract. The health probe itself cannot prove that an application has no other listening socket; verify the process/network table on the device before considering any wider exposure.

Run:

```bash
python garcar.py deploy example-api /path/to/application
python garcar.py status
python garcar.py verify-ledger
python garcar.py stop example-api
```

Deployment flow: copy source into a timestamped release, run build steps, start a canary on the canary port, require a 2xx health response, then start the candidate on the service port. If promotion fails, the prior release is restarted and rechecked. This is a local single-node release switch, not zero-downtime blue/green deployment.

## Security and recovery

- No automatic public exposure.
- No secrets in manifests, command-line arguments, or audit records.
- No live payment or billing operations.
- No automatic infrastructure purchases.
- No source repository is modified by a build or deployment; source is copied into a release directory.
- Failed health checks do not update the active release pointer.
- Audit hash chaining detects accidental or unsophisticated ledger alteration; it is not WORM storage and an administrator can rewrite the database and recompute the chain.
- Back up the state directory before upgrades. Do not delete releases until a restore test is complete.

## Acceptance tests

Run the test suite on the actual Termux device:

```bash
python -m unittest discover -s tests -v
```

Then deploy only a disposable local canary application. Verify status, logs, restart behavior, rollback, and ledger integrity. The existence of this source code does not mean those device tests have passed.
