"""Deny-by-default repository-scoped MCP gateway."""
from __future__ import annotations
import base64, hashlib, hmac, json, logging, os, time, uuid
from pathlib import Path
from typing import Any
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from approval import verify_approval

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/"policy.json").read_text())
REGISTRY=json.loads(Path(__file__).with_name("registry.json").read_text())
AUDIENCE=os.environ.get("MCP_GATEWAY_AUDIENCE","garcar-mcp")
ISSUER=os.environ.get("MCP_GATEWAY_ISSUER","garcar-control-plane")
SIGNING_KEY=os.environ.get("MCP_GATEWAY_SIGNING_KEY","").encode()
MAX_BODY=64_000
logging.basicConfig(level=logging.INFO,format="%(message)s")
log=logging.getLogger("mcp-audit")
app=FastAPI(title="Garcar MCP Gateway",docs_url=None,redoc_url=None)

class Invocation(BaseModel):
    server: str=Field(min_length=1,max_length=40)
    tool: str=Field(min_length=1,max_length=100)
    arguments: dict[str,Any]=Field(default_factory=dict)


def decode_segment(value:str)->bytes:
    return base64.urlsafe_b64decode(value+"="*(-len(value)%4))

def authenticate(header:str|None)->dict[str,Any]:
    if not SIGNING_KEY: raise HTTPException(503,"gateway identity verifier unavailable")
    if not header or not header.startswith("Bearer "): raise HTTPException(401,"repository identity required")
    token=header[7:]; parts=token.split(".")
    if len(parts)!=3: raise HTTPException(401,"invalid identity")
    signed=f"{parts[0]}.{parts[1]}".encode(); expected=hmac.new(SIGNING_KEY,signed,hashlib.sha256).digest()
    try: signature=decode_segment(parts[2]); claims=json.loads(decode_segment(parts[1]))
    except Exception: raise HTTPException(401,"invalid identity")
    if not hmac.compare_digest(signature,expected): raise HTTPException(401,"invalid identity")
    now=int(time.time())
    if claims.get("iss")!=ISSUER or claims.get("aud")!=AUDIENCE or claims.get("exp",0)<=now or claims.get("iat",now)>now+30: raise HTTPException(401,"expired or invalid identity")
    if not isinstance(claims.get("sub"),str): raise HTTPException(401,"repository identity missing")
    return claims

def scope_for(repository:str)->dict[str,Any]:
    name=repository.rsplit("/",1)[-1]; class_name=POLICY.get("repositories",{}).get(name,POLICY["defaults"]["classification"])
    return POLICY.get("classes",{}).get(class_name,POLICY["defaults"])

def audit(request_id:str,repository:str,server:str,tool:str,outcome:str)->None:
    log.info(json.dumps({"event":"mcp.invoke","request_id":request_id,"repository":repository,"server":server,"tool":tool,"outcome":outcome,"ts":int(time.time())},separators=(",",":")))

@app.middleware("http")
async def limits(request:Request,call_next):
    if int(request.headers.get("content-length","0") or 0) > MAX_BODY:
        return JSONResponse({"detail": "request too large"}, status_code=413)
    return await call_next(request)

@app.get("/health")
def health(): return {"status":"ok","policy_version":POLICY["version"],"registry_version":REGISTRY["version"]}

@app.get("/v1/capabilities")
def capabilities(authorization:str|None=Header(default=None)):
    claims=authenticate(authorization); scope=scope_for(claims["sub"]); allowed=set(scope.get("mcp_tools",[]))
    groups={}
    for group,tools in REGISTRY.get("capability_groups",{}).items():
        group_allowed=allowed.intersection(tools)
        if not group_allowed: level="unavailable"
        elif any(tool in REGISTRY["tool_classes"]["consequential"] for tool in group_allowed): level="approval-enabled"
        elif any(tool in REGISTRY["tool_classes"]["draft"] for tool in group_allowed): level="draft-enabled"
        else: level="read-only"
        groups[group]=level
    return {"repository":claims["sub"],"approval_enabled":bool(scope.get("human_approval_required")),"capability_groups":groups}

@app.post("/v1/invoke")
async def invoke(body:Invocation,authorization:str|None=Header(default=None),x_human_approval:str|None=Header(default=None)):
    request_id=str(uuid.uuid4()); claims=authenticate(authorization); repository=claims["sub"]; scope=scope_for(repository)
    if body.server not in scope.get("mcp_servers",[]) or body.tool not in scope.get("mcp_tools",[]):
        audit(request_id,repository,body.server,body.tool,"denied"); raise HTTPException(403,"tool not authorized")
    server=REGISTRY.get("servers",{}).get(body.server)
    if not server or body.tool not in server.get("tools",[]): raise HTTPException(403,"tool not registered")
    if body.tool in REGISTRY.get("tool_classes",{}).get("consequential",[]):
        try:
            approval=verify_approval(x_human_approval,repository,body.server,body.tool,body.arguments)
            audit(request_id,repository,body.server,body.tool,f"approved:{approval['actor']}")
        except ValueError as exc:
            audit(request_id,repository,body.server,body.tool,"approval_denied")
            raise HTTPException(403,str(exc)) from exc
    url=os.environ.get(server["url_env"],"")
    if not url: raise HTTPException(503,"upstream unavailable")
    # Provider credentials stay at the upstream MCP service/Vault boundary.
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.post(url,json={"jsonrpc":"2.0","id":request_id,"method":"tools/call","params":{"name":body.tool,"arguments":body.arguments}},headers={"X-Garcar-Repository":repository,"X-Request-ID":request_id})
            response.raise_for_status(); payload=response.json()
    except Exception:
        audit(request_id,repository,body.server,body.tool,"upstream_error"); raise HTTPException(502,"upstream MCP call failed")
    audit(request_id,repository,body.server,body.tool,"allowed")
    return {"request_id":request_id,"result":payload}
