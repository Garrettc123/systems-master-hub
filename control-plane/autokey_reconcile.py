#!/usr/bin/env python3
"""Least-privilege Vault-to-GitHub reconciliation without logging values."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request
from typing import Any
from resolve_policy import load_policy, resolve

def request_json(url: str, method="GET", body=None, headers=None) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method, headers={"Content-Type":"application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)

def login() -> str:
    addr=os.environ["VAULT_ADDR"].rstrip("/")
    response=request_json(f"{addr}/v1/auth/approle/login", "POST", {"role_id":os.environ["VAULT_ROLE_ID"], "secret_id":os.environ["VAULT_SECRET_ID"]})
    return response["auth"]["client_token"]

def read_value(token: str, name: str) -> str | None:
    try:
        response=request_json(f'{os.environ["VAULT_ADDR"].rstrip("/")}/v1/secret/data/garcar/{name}', headers={"X-Vault-Token":token})
        value=response.get("data",{}).get("data",{}).get("value")
        return value if isinstance(value,str) and value else None
    except Exception:
        return None

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=["dry-run","apply","reconcile"],default="dry-run"); parser.add_argument("--owner",default="Garrettc123"); args=parser.parse_args()
    policy=load_policy(); raw=subprocess.check_output(["gh","repo","list",args.owner,"--limit","500","--json","nameWithOwner,isArchived,isFork"],text=True)
    repos=[r for r in json.loads(raw) if not r["isArchived"] and not r["isFork"]]
    token=login() if args.mode != "dry-run" else None; missing=[]
    for repo in repos:
        name=repo["nameWithOwner"]; scope=resolve(name,policy); names=scope["secrets"]
        print(json.dumps({"repository":name,"classification":scope["classification"],"managed":scope["managed"],"secret_names":names,"mode":args.mode},separators=(",",":")))
        if not token: continue
        for secret_name in names:
            if secret_name in {"GHPAT","VAULT_ROLE_ID","VAULT_SECRET_ID"} and name != f"{args.owner}/systems-master-hub": continue
            value=read_value(token,secret_name)
            if value is None: missing.append(f"{name}:{secret_name}"); continue
            subprocess.run(["gh","secret","set",secret_name,"--repo",name,"--body",value],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if missing:
        print(json.dumps({"missing_secret_names":missing}),file=sys.stderr); raise SystemExit(2)
if __name__ == "__main__": main()
