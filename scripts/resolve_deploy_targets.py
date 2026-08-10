#!/usr/bin/env python3
"""Resolve deploy targets from the canonical repo registry.

The registry (``registry/repos.json``) is the single source of truth for which
repositories exist and in what order they deploy. Adding a repo there is the
only step required for it to be picked up by the deploy pipeline — no workflow
edits, no hardcoded repo names.

Usage:
    resolve_deploy_targets.py --tier tier1        # matrix for one tier
    resolve_deploy_targets.py --all               # matrix for every tier
    resolve_deploy_targets.py --list-tiers        # ordered tier names
"""

import argparse
import json
import os
import sys

DEFAULT_REGISTRY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "registry",
    "repos.json",
)

# Deploy order. Tier-1 must be healthy before Tier-2 starts, and so on.
TIER_ORDER = ["tier1", "tier2", "tier3"]


def load_registry(path):
    """Read and minimally validate the registry file."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            registry = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"error: registry not found at {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: registry is not valid JSON: {exc}")

    if not isinstance(registry, dict):
        raise SystemExit("error: registry root must be an object")
    return registry


def targets_for_tier(registry, tier):
    """Return the deploy targets declared for a single tier."""
    repos = (registry.get(tier) or {}).get("repos") or {}
    targets = []
    for name, meta in sorted(repos.items()):
        meta = meta or {}
        full_name = meta.get("repo")
        if not full_name or "/" not in full_name:
            raise SystemExit(
                f"error: {tier}.{name} is missing a valid 'repo' field "
                f"(expected 'owner/name', got {full_name!r})"
            )
        owner, _, short = full_name.partition("/")
        targets.append(
            {
                "name": name,
                "repo": full_name,
                "owner": owner,
                "short": short,
                "tier": tier,
                "role": meta.get("role", "unknown"),
                "platform": meta.get("platform", "github-actions"),
                "dispatchEvent": meta.get("dispatchEvent") or "",
                "requiredSecrets": meta.get("requiredSecrets", []),
            }
        )
    return targets


def emit(payload, github_output, key):
    """Print the payload and, when running in Actions, record it as a step output."""
    text = json.dumps(payload, separators=(",", ":"))
    print(text)
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"{key}={text}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY,
                        help="path to repos.json (default: registry/repos.json)")
    parser.add_argument("--tier", choices=TIER_ORDER,
                        help="emit a matrix for a single tier")
    parser.add_argument("--all", action="store_true",
                        help="emit a matrix containing every tier")
    parser.add_argument("--list-tiers", action="store_true",
                        help="emit the ordered list of tier names")
    parser.add_argument("--output-key", default="matrix",
                        help="step output name to write (default: matrix)")
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    github_output = os.environ.get("GITHUB_OUTPUT")

    if args.list_tiers:
        emit(TIER_ORDER, github_output, args.output_key)
        return 0

    if args.tier:
        targets = targets_for_tier(registry, args.tier)
    elif args.all:
        targets = [t for tier in TIER_ORDER for t in targets_for_tier(registry, tier)]
    else:
        parser.error("one of --tier, --all or --list-tiers is required")

    # An empty matrix would make the downstream job fail rather than no-op, so
    # callers check the companion `count` output before running the matrix job.
    emit({"include": targets}, github_output, args.output_key)
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"count={len(targets)}\n")
    print(f"resolved {len(targets)} target(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
