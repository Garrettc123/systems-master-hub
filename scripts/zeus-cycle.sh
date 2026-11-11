#!/usr/bin/env bash
# ZEUS cycle: real service observations and optional signed, L0-only dispatch.
# Usage: bash scripts/zeus-cycle.sh "directive" "scope" 5000
set -Eeuo pipefail
if [[ $# -ne 3 ]]; then
  echo 'Usage: bash scripts/zeus-cycle.sh "DIRECTIVE" "SCOPE" WORK_UNIT_CEILING' >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo 'BLOCKED: python3 is required (Python 3.9+).' >&2
  exit 3
fi
exec python3 - "$@" <<'PY'
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
import uuid

DIRECTIVE, SCOPE, BUDGET_RAW = sys.argv[1:]
MODE = os.getenv('ZEUS_MODE', 'observe')
OUTPUT = Path.cwd() / '.zeus' / 'receipts'
RUN_ID = str(uuid.uuid4())


def block(reason):
    print('BLOCKED: ' + reason, file=sys.stderr)
    return 3


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(url, method='GET', data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=10) as response:
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('response exceeds 64 KiB')
        if not 200 <= response.status < 300:
            raise ValueError('unexpected HTTP status')
        return response.status, raw, response.headers


def safe_observe(name, url, expected):
    try:
        code, raw, _ = fetch_json(url)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError('response is not a JSON object')
        if expected is not None and parsed.get('status') != expected:
            return {'id': name, 'state': 'unverified', 'http_status': code,
                    'reason': 'unexpected status field', 'observed_status': str(parsed.get('status'))[:80]}
        return {'id': name, 'state': 'responding', 'http_status': code,
                'evidence': 'live HTTPS response', 'observed_status': str(parsed.get('status'))[:80]}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {'id': name, 'state': 'blocked', 'reason': type(exc).__name__}


def signed_l0(key, agent, objective):
    if len(key) < 48:
        raise ValueError('EVE_L0_DISPATCH_KEY must be at least 48 characters')
    path = '/api/eve/l0/dispatch'
    url = 'https://garcar-rhns-command-center-production.up.railway.app' + path
    timestamp = str(int(time.time() * 1000))
    nonce = secrets.token_urlsafe(24)
    request_id = uuid.uuid4().hex
    payload = {'agentId': agent, 'objective': objective, 'requestId': request_id}
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    body_hash = hashlib.sha256(body).hexdigest()
    signing = f'POST\n{path}\n{timestamp}\n{nonce}\n{body_hash}'.encode('utf-8')
    sig = hmac.new(key.encode(), signing, hashlib.sha256).hexdigest()
    code, raw, headers = fetch_json(url, 'POST', body, {
        'Content-Type': 'application/json',
        'X-Eve-Timestamp': timestamp,
        'X-Eve-Nonce': nonce,
        'X-Eve-Signature': sig,
    })
    expected_response_sig = hmac.new(key.encode(),
        f'{timestamp}\n{nonce}\n'.encode('utf-8') + raw, hashlib.sha256).hexdigest()
    returned_sig = headers.get('X-Eve-Response-Signature', '')
    if not hmac.compare_digest(returned_sig, expected_response_sig):
        raise ValueError('invalid signed response')
    result = json.loads(raw)
    receipt = result.get('receipt', {})
    if (result.get('status') != 'completed_local' or receipt.get('status') != 'completed_local'
        or receipt.get('effect') != 'none' or not result.get('ledgerEventHash')
        or any(result.get(flag) is not False for flag in (
            'externalMessagesSent', 'paymentActionsExecuted', 'crmRecordsModified'))):
        raise ValueError('signed receipt did not satisfy L0 constraints')
    return {'agent': agent, 'state': 'completed_local', 'http_status': code,
            'receipt_id': receipt.get('id'), 'receipt_digest': receipt.get('digest'),
            'ledger_event_hash': result['ledgerEventHash'],
            'started_at': receipt.get('startedAt'), 'finished_at': receipt.get('finishedAt'),
            'external_effects': False}


def main():
    if not DIRECTIVE.strip() or not SCOPE.strip() or len(DIRECTIVE) > 1000 or len(SCOPE) > 500:
        return block('nonempty directive and scope are required')
    if not re.fullmatch(r'[1-9][0-9]{0,5}', BUDGET_RAW):
        return block('work-unit ceiling must be a positive integer')
    budget = int(BUDGET_RAW)
    if budget > 5000:
        return block('work-unit ceiling exceeds maximum 5000')
    if MODE not in ('observe', 'l0'):
        return block('ZEUS_MODE must be observe or l0')
    if MODE == 'l0' and len(os.getenv('EVE_L0_DISPATCH_KEY', '')) < 48:
        return block('missing or invalid signed L0 dispatch key; no request sent')
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    observations = [
        safe_observe('rhns-command-center',
          'https://garcar-rhns-command-center-production.up.railway.app/api/health', 'operational'),
        safe_observe('garcar-revenue-app',
          'https://garcar-revenue-app-production.up.railway.app/health', None),
    ]
    # Repo manifests and a successful deployment do not establish remote identity.
    limitations = [
        {'id': 'sovereign-autonomy-worker', 'state': 'unverified',
         'reason': 'no authenticated runtime receipt available to this script'},
        {'id': 'bioforge-organs', 'state': 'unverified',
         'reason': 'source manifest exists, deployed organ endpoint not verified'},
        {'id': 'axiom-12', 'state': 'missing',
         'reason': 'no verified implementation or authenticated endpoint'},
    ]
    dispatches = []
    if MODE == 'l0':
        if observations[0]['state'] != 'responding':
            limitations.append({'id': 'l0-dispatch', 'state': 'blocked',
                                'reason': 'RHNS health check failed; no directives sent'})
        else:
            tasks = [
                ('observer', 'Inspect local operational evidence and unresolved blockers; do not execute external actions.'),
                ('governance', 'Review local approvals and governance state; do not execute external actions.'),
                ('revenue_intelligence', 'Analyze only locally verified revenue signals; do not send or charge.'),
                ('ceo', 'Prioritize verified next actions for one paying customer; do not send or charge.'),
            ]
            for agent, objective in tasks:
                try:
                    dispatches.append(signed_l0(os.environ['EVE_L0_DISPATCH_KEY'], agent, objective))
                except (urllib.error.URLError, TimeoutError, OSError, ValueError,
                        json.JSONDecodeError, KeyError) as exc:
                    dispatches.append({'agent': agent, 'state': 'blocked',
                                       'reason': type(exc).__name__})
                    break  # Fail closed; never fan out after failed authorization/proof.
    complete = (MODE == 'l0' and len(dispatches) == 4
                and all(d['state'] == 'completed_local' for d in dispatches)
                and all(x['state'] == 'responding' for x in observations)
                and not limitations)
    status = 'completed' if complete else 'blocked_incomplete'
    report = {'schema_version': 1, 'run_id': RUN_ID, 'started_at': started,
              'finished_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'directive': DIRECTIVE, 'scope': SCOPE, 'mode': MODE,
              'work_unit_ceiling': budget, 'work_units_executed': len(dispatches),
              'status': status, 'observations': observations,
              'signed_l0_receipts': dispatches, 'limitations': limitations,
              'no_outbound_messages_or_payment_actions_requested': True,
              'evidence_type': 'local report; not independently immutable'}
    digest = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    report['local_report_sha256'] = digest
    OUTPUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUTPUT, 0o700)
    path = OUTPUT / (RUN_ID + '.json')
    with path.open('x', encoding='utf-8') as fp:
        os.chmod(path, 0o600)
        json.dump(report, fp, indent=2)
        fp.write('\n')
    print(json.dumps({'run_id': RUN_ID, 'status': status, 'mode': MODE,
                      'work_units_executed': len(dispatches),
                      'observations': observations, 'receipts': dispatches,
                      'limitations': limitations, 'report_path': str(path),
                      'local_report_sha256': digest}, indent=2))
    return 0 if complete else 3


sys.exit(main())
PY
