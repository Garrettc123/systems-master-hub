# Full-stack validation evidence

The recorded run has 108 passing tests and passing real-process, persistence, backup/restore, promotion/rollback, syntax, dependency, lint, and package checks. Its result is `local_canary_passed_host_check_blocked`, not production completion.

- [Completion result and gates](completion.json)
- [Phone, Forge, Actions, persistent-lead restart, and backup/restore canary](full-stack-smoke.json)
- [Promotion and rollback canary](sovereign-smoke.json)
- [Actions API/worker canary](actions/local-smoke.json)
- [Pinned hub structure port](actions/hub-canary.json)
- [57-workflow inventory](hub-workflows.json)
- [Read-only Railway snapshot](railway-snapshot.json)
- [Integrated source revisions](provenance.json)
- [Source fingerprints](source-sha256.json)

The host blocks `/proc` environment inspection needed by the Termux PID guard. It is recorded as blocked and contributes no passing tests. The runner exits 2 while this or production readiness remains unresolved. The cloud worker repair is published in tree-of-life-system PR 180; this run did not deploy it. Customer payments were not checked.

Test logs are stored as individual text files named for each stage. The source fingerprint identifies the code and configuration used by the integration run; generated reports are outside that fingerprint. Source workflow classifications and declared inventory counts are not evidence of live deployment.
