"""Read-only structural checks. Passing does not prove runtime health."""
import json
from pathlib import Path


def audit(root):
    checks = []
    def add(name, status, evidence):
        checks.append(dict(check=name, status=status, evidence=evidence))
    generated = root / 'registry/registry.json'
    if not generated.exists():
        add('generated_registry', 'FAIL', 'registry/registry.json missing')
    else:
        try:
            data = json.loads(generated.read_text(encoding='utf-8'))
            valid = isinstance(data, dict) and isinstance(data.get('systems'), list) and bool(data.get('generated_at'))
            add('generated_registry', 'PASS' if valid else 'FAIL', 'Checked structure only; completeness and freshness NOT VERIFIED')
        except (ValueError, OSError) as exc:
            add('generated_registry', 'FAIL', str(exc))
    for name in ['registry/sync.py', 'ledger/api.py', 'ledger/gc_ledger.py', 'packages/garcar_bus/bus.py']:
        add('source:' + name, 'PASS' if (root / name).is_file() else 'FAIL', name)
    for name in ['registry-daily-sync.yml', 'upgrade-all.yml', 'nightly-upgrade-loop.yml']:
        path = root / '.github/workflows' / name
        if path.is_file():
            text = path.read_text(encoding='utf-8')
            add('workflow:' + name, 'REVIEW', 'Manual review required; contains failure suppression: ' + str('|| true' in text))
    add('runtime_health', 'NOT_VERIFIED', 'No deployment, provider, payment or workflow execution probed')
    return checks


if __name__ == '__main__':
    results = audit(Path(__file__).resolve().parents[1])
    print(json.dumps({'checks': results}, indent=2))
    raise SystemExit(1 if any(c['status'] == 'FAIL' for c in results) else 0)
