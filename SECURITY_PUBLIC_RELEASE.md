# Garcar Public Release Safety Contract

## Release gate

Garcar MUST NOT be marked public-production-ready until every applicable gate below passes.

1. **Identity & authorization**
   - Default-deny authorization.
   - Least-privilege service identities.
   - Production deployment requires an explicit protected environment approval.

2. **Secrets & cryptography**
   - No plaintext credentials in Git, artifacts, logs, telemetry, or issue reports.
   - Secrets referenced by identifier only.
   - Rotation tested before credential revocation.
   - Production key material remains in an approved secrets/KMS boundary.

3. **Software supply chain**
   - Dependency and secret scanning pass.
   - Reproducible/pinned build inputs where practical.
   - Release artifact provenance recorded.
   - SBOM generated for production artifacts.
   - Critical unresolved vulnerabilities block release.

4. **Application security**
   - Authentication and authorization tests pass.
   - Input validation and output encoding are tested.
   - Rate limits and abuse controls exist for public endpoints.
   - Secure error handling prevents secret/internal-state disclosure.
   - Administrative endpoints are not publicly exposed by default.

5. **AI safety**
   - Model output is treated as untrusted data.
   - Tool use requires explicit capability and policy authorization.
   - High-impact actions require deterministic policy checks.
   - Autonomous agents cannot grant themselves permissions.
   - Agent completion is not treated as proof of successful execution; observable postconditions are required.
   - External side effects are idempotent where feasible.

6. **Privacy & data governance**
   - Collect only data required for the stated purpose.
   - Sensitive data is minimized and access-controlled.
   - Retention/deletion rules are documented.
   - Public telemetry contains no customer secrets or unnecessary personal data.

7. **Reliability**
   - Health and readiness checks exist.
   - Backups exist and restoration has been tested.
   - Rollback is tested and non-destructive by default.
   - Production deployments are concurrency-controlled.
   - Monitoring and alerting cover critical user journeys.

8. **Public exposure**
   - TLS is enforced.
   - Security headers and safe CORS policy are configured.
   - Public API abuse/rate limiting is enabled.
   - No debug mode, test credentials, staging admin routes, or development consoles are exposed.
   - A vulnerability-reporting channel is published before general availability.

9. **Evidence**
   - Commit/artifact digest recorded.
   - Deployment identity recorded.
   - Environment recorded.
   - Test/security results recorded.
   - Health-check evidence recorded.
   - Release decision is reproducible from the evidence bundle.

## Fail-closed rule

A failed, unknown, missing, or unverifiable control blocks public production release. No workflow may convert an unknown state into `PASS` through `continue-on-error`, silent fallback, or inferred infrastructure state.

## Emergency rule

Emergency containment may disable service, revoke credentials, isolate workloads, or roll back to a known-good artifact. Destructive infrastructure actions require an explicit, separately authorized recovery procedure.

## Reference baseline

This contract is aligned to the NIST Secure Software Development Framework (SSDF), including practices for preparing the organization, protecting software, producing well-secured software, and responding to vulnerabilities. It should be treated as a risk-based baseline rather than a certification claim.
