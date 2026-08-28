#!/usr/bin/env python3
"""Generate reviewable repository contracts; never writes secrets."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
from resolve_policy import load_policy, resolve

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--owner",default="Garrettc123"); parser.add_argument("--output",default="control-plane/generated"); args=parser.parse_args()
    repos=json.loads(subprocess.check_output(["gh","repo","list",args.owner,"--limit","500","--json","nameWithOwner,isArchived,isFork,visibility"],text=True))
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True); policy=load_policy(); index=[]
    for repo in repos:
        if repo["isArchived"] or repo["isFork"]: continue
        scope=resolve(repo["nameWithOwner"],policy)
        contract={"version":1,"repository":repo["nameWithOwner"],"classification":scope["classification"],"managed":scope["managed"],"mcp":{"gateway_env":"MCP_GATEWAY_URL","audience_env":"MCP_GATEWAY_AUDIENCE","servers":scope["mcp_servers"],"tools":scope["mcp_tools"]},"secret_names":scope["secrets"]}
        path=out/f'{repo["nameWithOwner"].split("/")[-1]}.json'; path.write_text(json.dumps(contract,indent=2)+"\n"); index.append({"repository":repo["nameWithOwner"],"contract":str(path),"managed":scope["managed"]})
    (out/"index.json").write_text(json.dumps(index,indent=2)+"\n")
if __name__ == "__main__": main()
