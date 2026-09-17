# Perplexity Control Center

Perplexity is the designated control center for Garcar Enterprise.

## Authority model

Perplexity:
- observes system state and external intelligence
- reasons over available evidence
- establishes operating directives and limits
- coordinates Garcar systems

Garcar:
- executes directives through connected services
- records state and evidence
- runs RHNS reasoning and CRF reliability workflows

Supabase:
- operational system of record
- stores opportunities, evidence, decisions, workflow state, and audit data

GitHub:
- source of truth for code, manifests, contracts, workflows, and system inventory

## Control loop

Perplexity -> Garcar control interface -> execution -> Supabase evidence/state -> Perplexity feedback

## Repository contract

Every managed repository should expose:
- system identity
- capabilities
- dependencies
- health status
- deployment metadata
- owner/control metadata
- CRF compatibility
- revenue relevance
- operational evidence

This file defines architecture only; it does not claim that a direct Perplexity API connection is currently installed.