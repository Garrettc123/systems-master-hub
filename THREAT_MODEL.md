# Garcar Public Threat Model

## Assets

- Customer and account data
- Authentication/session material
- API and database credentials
- Signing/encryption keys
- AI agent capabilities and tool permissions
- Production infrastructure
- Deployment artifacts
- Financial and billing events
- Audit/evidence records

## Primary threats

- Credential theft or replay
- Supply-chain compromise
- Unauthorized deployment
- Privilege escalation
- Prompt injection/tool abuse
- Data exfiltration
- Public API abuse and denial of service
- Webhook forgery/replay
- Dependency vulnerabilities
- Configuration drift
- Accidental destructive automation
- Cross-tenant data access

## Required controls

### Prevent

Least privilege, default deny, protected deployment environments, secret isolation, dependency pinning/scanning, input validation, tenant isolation, rate limiting, webhook signature verification, and AI tool authorization.

### Detect

Centralized audit events, authentication anomalies, deployment events, secret access, failed authorization, dependency alerts, runtime health, and financial reconciliation anomalies.

### Respond

Credential rotation, session invalidation, workload isolation, deployment freeze, rollback to known-good artifacts, incident evidence preservation, and controlled recovery.

### Recover

Verified backups, tested restoration, reproducible builds, infrastructure-as-code, immutable release evidence, and post-incident regression tests.

## AI-specific boundary

An AI agent may propose an action but does not thereby receive authorization to execute it. Tool access is capability-scoped and policy-controlled. Sensitive side effects require deterministic authorization and postcondition verification.

## Public-release principle

Unknown security state is a failure state. The system must fail closed instead of inferring safety from repository presence, model confidence, successful compilation, or an agent's self-report.
