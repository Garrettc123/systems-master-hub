# HARDENING PLAYBOOK — Government Official Standard
## Least Privilege • SBOM • BioForge Certification

### A. Workflow Permissions Template

```yaml
permissions:
  contents: read
  # Add only what is required:
  # pull-requests: write
  # security-events: write
  # id-token: write
```

### B. Canonical SECURITY.md
See `CANONICAL_SECURITY.md` in this directory.

### C. CycloneDX SBOM
```bash
cyclonedx-py environment --of json -o sbom.json
```
Attach as release asset on production builds.

### D. Six BioForge Certification Gates (hard gate)
1. Contract first (manifest + ports)  
2. RHNS binding declared  
3. Detach + rollback procedure present  
4. CMC `commit` on every monetizing hop  
5. SBOM + observability enrollment  
6. Pricing metadata present  

Refuse attach if any gate fails.

### E. Priority Repos
Tier 0: systems-master-hub, autonomous-butler-core, autonomous-income-deployment, pi-control-plane, garcar-revenue-os  
Tier 1: GARCAR-SECURITY-OPS, VAULT, NEXUS-COMPLIANCE, AI-GOVERNANCE  

### F. Expansion
Use `scripts/EXPAND_AUTO_FIX.sh` and `scripts/sync-docs.sh --apply` with auth.
