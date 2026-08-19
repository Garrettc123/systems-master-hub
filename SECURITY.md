# Security Policy

## Reporting a vulnerability

Do not publish credentials, exploit details, customer data, or other sensitive material in public issues.

Use the repository's configured private vulnerability-reporting mechanism when available. If none is configured, open a minimal public issue containing only the affected component and the words `SECURITY REPORT NEEDED`; do not include exploit code or secrets.

## Response objectives

Security reports are triaged by severity and impact. Confirmed issues may result in deployment freezes, credential rotation, workload isolation, or emergency rollback.

## Secret exposure

If a secret is exposed, treat it as compromised immediately. Do not merely delete it from the current branch. Revoke/rotate it at the provider, invalidate dependent sessions where applicable, investigate access logs, and preserve incident evidence.

## Scope

The security boundary includes source code, CI/CD, cloud infrastructure, APIs, databases, secrets, AI agent tools, customer data, and deployment artifacts.
