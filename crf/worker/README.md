# GARCAR CRF Repair Worker

CRF is a governed continuous reliability control plane.

## Lifecycle

`OBSERVED -> NORMALIZED -> CLUSTERED -> DIAGNOSED -> REPAIR_PROPOSED -> POLICY_CHECK -> VERIFY -> VERIFIED -> DRAFT_PR -> APPROVED -> MERGED -> MONITORED -> RESOLVED|REGRESSED`

## Safety

- Default autonomy: Level 2.
- Workers may diagnose and prepare repairs.
- Production merge requires an explicit approval record.
- Repairs are scoped to the affected tenant/system/repository.
- Every stage emits evidence and an auditable attempt record.
- Locks prevent duplicate concurrent execution.
- Failed verification blocks PR creation.

## Worker contract

1. Claim repairs through `crf_claim_repairs`.
2. Record a `crf_repair_attempts` row for each stage.
3. Never mutate a repository without a policy-approved repair.
4. Verify before opening a PR.
5. Create a draft PR containing the diagnosis, evidence, tests, risk score, and rollback plan.
6. Release the repair lock.
7. Monitor the resulting deployment and record outcome.

## Commercial tenancy

CRF supports customer isolation. The standard Garcar offer is $3,000 implementation plus $300/month recurring service.
