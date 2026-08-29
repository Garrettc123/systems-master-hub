#!/usr/bin/env python3
"""Resolve repository secret and MCP scopes without reading secret values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POLICY_PATH = Path(__file__).with_name("policy.json")


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = json.loads(path.read_text())
    if policy.get("version") not in {1, 2}:
        raise ValueError("unsupported policy version")
    return policy


def resolve(repository: str, policy: dict[str, Any]) -> dict[str, Any]:
    repo_name = repository.rsplit("/", 1)[-1]
    class_name = policy.get("repositories", {}).get(
        repo_name, policy["defaults"]["classification"]
    )
    class_policy = policy.get("classes", {}).get(class_name, policy["defaults"])
    return {
        "repository": repository,
        "classification": class_name,
        "secrets": sorted(set(class_policy.get("secrets", []))),
        "mcp_servers": sorted(set(class_policy.get("mcp_servers", []))),
        "mcp_tools": sorted(set(class_policy.get("mcp_tools", []))),
        "capability_groups": sorted(set(class_policy.get("capability_groups", []))),
        "human_approval_required": class_policy.get("human_approval_required", False) is True,
        "managed": class_name != "unclassified",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository")
    parser.add_argument("--field", choices=["classification", "secrets", "mcp_servers", "mcp_tools"])
    args = parser.parse_args()
    result = resolve(args.repository, load_policy())
    value = result[args.field] if args.field else result
    if isinstance(value, list):
        print("\n".join(value))
    elif isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
