#!/usr/bin/env python3
"""Read-only Garcar operator checks. Nothing here deploys, writes to GitHub,
contacts prospects, moves funds, reads secret values or modifies remote repos.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

IGNORED = {'.git', 'node_modules', '.venv', 'venv', '__pycache__',
           'dist', 'build', '.next', '.pytest_cache', '.mypy_cache',
           'operator-evidence', 'external-operator-evidence'}
SIZE_LIMIT = 2_000_000
GITHUB_REPO = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$')
SENSITIVE_NAMES = {'.env', '.env.local', '.env.production', 'credentials.json',
                   'service-account.json', 'id_rsa', 'id_ed25519', 'id_ecdsa'}
SECRET_PATTERNS = {
    'aws_access_key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github_personal_access_token': re.compile(r'\b(?:ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9]{32,}\b'),
    'github_fine_grained_token': re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
    'stripe_live_key': re.compile(r'\b(?:sk_live_|rk_live_)[A-Za-z0-9]{16,}\b'),
    'private_key_header': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
}
SOURCE_SUFFIXES = {'.py', '.sh', '.json', '.yaml', '.yml', '.js', '.mjs', '.ts', '.md', '.toml'}


def paths(root: Path, suffixes: set[str] | None = None):
    """Stable, path-safe file enumeration; do not follow symlinks."""
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            file = Path(base) / name
            if file.is_symlink() or (suffixes is not None and file.suffix.lower() not in suffixes):
                continue
            yield file


def rel(file: Path, root: Path) -> str:
    return file.relative_to(root).as_posix()


def bounded_text(file: Path) -> str:
    if file.stat().st_size > SIZE_LIMIT:
        raise ValueError('file exceeds scan size limit')
    return file.read_text(encoding='utf-8')


def fresh_report(action: str) -> dict:
    return {'schema': 'garcar.operator.manual.v2', 'action': action,
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'unknown', 'checks': [], 'warnings': [], 'errors': [], 'totals': {},
            'notes': ['Read-only inspection; no deployment, customer outreach, fund movement, or repo mutations.']}


def record(report: dict, name: str, outcome: str, detail: str):
    assert outcome in ('pass', 'fail', 'warning', 'info')
    report['checks'].append({'name': name, 'status': outcome, 'detail': detail})
    if outcome == 'fail':
        report['errors'].append(name + ': ' + detail)
    elif outcome == 'warning':
        report['warnings'].append(name + ': ' + detail)


def load_inventory(root: Path, report: dict) -> dict | None:
    path = root / 'SYSTEMS-INVENTORY.json'
    if not path.is_file():
        record(report, 'inventory', 'fail', 'SYSTEMS-INVENTORY.json missing')
        return None
    try:
        data = json.loads(bounded_text(path))
        if not isinstance(data, dict) or not isinstance(data.get('categories'), dict):
            raise ValueError('categories must be a dictionary')
        return data
    except (OSError, ValueError, UnicodeError) as exc:
        record(report, 'inventory', 'fail', 'Inventory file cannot be parsed as expected: ' + type(exc).__name__)
        return None


def validate_all(root: Path, report: dict):
    try:
        import yaml
    except ImportError:
        record(report, 'YAML parser dependency', 'fail', 'PyYAML is not installed')
        return
    # YAML 1.1 SafeLoader turns GitHub Actions' `on:` key into True. Parse
    # bool words as strings for structural inspection; this is not actionlint.
    class GithubLoader(yaml.SafeLoader):
        pass
    GithubLoader.yaml_implicit_resolvers = {
        k: [(tag, regex) for tag, regex in v if tag != 'tag:yaml.org,2002:bool']
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    counts = {'yaml_checked': 0, 'shell_checked': 0, 'json_checked': 0,
              'compose_checked': 0, 'compose_warnings': 0}
    for file in paths(root, {'.yaml', '.yml'}):
        key = rel(file, root)
        counts['yaml_checked'] += 1
        try:
            doc = yaml.load(bounded_text(file), Loader=GithubLoader)
            if key.startswith('.github/workflows/') and (not isinstance(doc, dict)
                    or 'on' not in doc or not isinstance(doc.get('jobs'), dict)):
                record(report, key, 'fail', 'GitHub workflow missing on/jobs mappings')
            else:
                record(report, key, 'pass', 'YAML syntax parsed')
        except (OSError, UnicodeError, ValueError, yaml.YAMLError):
            record(report, key, 'fail', 'YAML parse failed (details withheld)')
    for file in paths(root, {'.sh'}):
        key = rel(file, root)
        counts['shell_checked'] += 1
        try:
            result = subprocess.run(['bash', '-n', str(file)], capture_output=True,
                                    timeout=10, check=False)
            record(report, key, 'pass' if result.returncode == 0 else 'fail',
                   'bash -n passed' if result.returncode == 0 else 'bash -n rejected file')
        except (OSError, subprocess.TimeoutExpired):
            record(report, key, 'fail', 'Shell syntax check failed to execute')
    for file in paths(root, {'.json'}):
        key = rel(file, root)
        counts['json_checked'] += 1
        try:
            json.loads(bounded_text(file))
            record(report, key, 'pass', 'JSON syntax parsed')
        except (OSError, ValueError, UnicodeError):
            record(report, key, 'fail', 'JSON parse failed')
    composes = [p for p in paths(root, {'.yaml', '.yml'})
                if p.name.startswith(('docker-compose', 'compose.'))]
    for file in composes:
        key = rel(file, root)
        counts['compose_checked'] += 1
        try:
            result = subprocess.run(['docker', 'compose', '-f', str(file), 'config', '--quiet',
                                     '--no-interpolate'], cwd=file.parent,
                                    capture_output=True, timeout=25, check=False)
            if result.returncode == 0:
                record(report, key + ' / compose', 'pass', 'Compose configuration parsed')
            else:
                counts['compose_warnings'] += 1
                record(report, key + ' / compose', 'warning',
                       'Compose config unavailable or invalid; validate in deployment environment')
        except (OSError, subprocess.TimeoutExpired):
            counts['compose_warnings'] += 1
            record(report, key + ' / compose', 'warning', 'Docker Compose unavailable or timed out')
    report['totals'] = counts


def inventory_report(root: Path, report: dict):
    data = load_inventory(root, report)
    counts = {k: 0 for k in ('workflows', 'shell_scripts', 'compose_files', 'markdown_files', 'categories', 'catalog_entries', 'distinct_linked_repos')}
    allfiles = list(paths(root))
    counts['workflows'] = sum(1 for p in allfiles if rel(p, root).startswith('.github/workflows/') and p.suffix in ('.yml', '.yaml'))
    counts['shell_scripts'] = sum(p.suffix == '.sh' for p in allfiles)
    counts['compose_files'] = sum(p.suffix in ('.yml', '.yaml') and p.name.startswith(('docker-compose', 'compose.')) for p in allfiles)
    counts['markdown_files'] = sum(p.suffix == '.md' for p in allfiles)
    if data is not None:
        categories = data['categories']
        counts['categories'] = len(categories)
        if not all(isinstance(v, dict) for v in categories.values()):
            record(report, 'inventory.schema', 'fail', 'Inventory categories must contain dictionaries')
        else:
            entries = [entry for category in categories.values() for entry in category.values()]
            counts['catalog_entries'] = len(entries)
            urls = {e.get('repo_url') for e in entries if isinstance(e, dict) and isinstance(e.get('repo_url'), str)}
            counts['distinct_linked_repos'] = len(urls)
            overview = data.get('overview', {})
            report['inventory_overview_claims'] = {
                'last_updated': overview.get('last_updated'),
                'declared_total_repositories': overview.get('total_repositories'),
                'declared_production_systems': overview.get('production_systems')}
            record(report, 'historical_inventory', 'warning',
                   'Inventory overview totals and status are declarations, not current GitHub or production verification')
    report['totals'] = counts


def external_repos(root: Path, report: dict):
    data = load_inventory(root, report)
    if data is None:
        return
    urls = sorted({e.get('repo_url') for c in data['categories'].values() if isinstance(c, dict)
                   for e in c.values() if isinstance(e, dict) and isinstance(e.get('repo_url'), str)})
    stats = {'declared_url_count': len(urls), 'accessible': 0, 'unverified_or_inaccessible': 0,
             'malformed_url': 0}
    # GitHub Actions GITHUB_TOKEN is limited to its own repository by default.
    # Failure is unknown accessibility, not proof of deletion or privacy.
    for url in urls:
        match = GITHUB_REPO.fullmatch(url)
        if not match:
            stats['malformed_url'] += 1
            record(report, 'repository URL', 'warning', 'Malformed or unsupported GitHub repository URL')
            continue
        repo = match.group(1) + '/' + match.group(2)
        if not os.environ.get('GH_TOKEN'):
            stats['unverified_or_inaccessible'] += 1
            record(report, repo, 'warning', 'No GitHub token available to check visibility')
            continue
        try:
            response = subprocess.run(['gh', 'repo', 'view', repo, '--json', 'name', '-q', '.name'],
                                      cwd=root, capture_output=True, timeout=20, check=False)
            if response.returncode == 0:
                stats['accessible'] += 1
                record(report, repo, 'pass', 'Repository accessible with current token')
            else:
                stats['unverified_or_inaccessible'] += 1
                record(report, repo, 'warning',
                       'Repository not accessible to this token; existence/private status unverified')
        except (OSError, subprocess.TimeoutExpired):
            stats['unverified_or_inaccessible'] += 1
            record(report, repo, 'warning', 'GitHub API check unavailable or timed out')
    report['totals'] = stats


def security_scan(root: Path, report: dict):
    stats = {'files_scanned': 0, 'possible_secret_matches': 0, 'sensitive_files': 0,
             'workflow_files_reviewed': 0, 'workflow_permission_warnings': 0}
    for file in paths(root):
        key = rel(file, root)
        if file.name in SENSITIVE_NAMES or file.name.startswith('.env.'):
            stats['sensitive_files'] += 1
            record(report, key, 'warning', 'Sensitive filename committed; inspect and rotate any exposed credentials')
        if file.suffix not in SOURCE_SUFFIXES:
            continue
        try:
            source = bounded_text(file)
        except (OSError, UnicodeError, ValueError):
            continue
        stats['files_scanned'] += 1
        types = [type_name for type_name, regex in SECRET_PATTERNS.items() if regex.search(source)]
        if types:
            stats['possible_secret_matches'] += 1
            record(report, key, 'warning', 'Potential secret pattern type(s): ' + ', '.join(types) + '; VALUE WITHHELD')
    for file in paths(root, {'.yml', '.yaml'}):
        if not rel(file, root).startswith('.github/workflows/'):
            continue
        stats['workflow_files_reviewed'] += 1
        try:
            source = bounded_text(file)
        except (OSError, UnicodeError, ValueError):
            continue
        if not re.search(r'(?m)^permissions\s*:', source):
            stats['workflow_permission_warnings'] += 1
            record(report, rel(file, root), 'warning', 'No top-level permissions block; job permissions and repository defaults require review')
        if re.search(r'(?m)^\s*(?:contents|id-token|actions|packages|deployments|security-events)\s*:\s*write\s*(?:#.*)?$', source):
            stats['workflow_permission_warnings'] += 1
            record(report, rel(file, root), 'warning', 'Workflow contains a write permission; evaluate least privilege per job')
    record(report, 'security_scan_scope', 'info',
           'Heuristic working-tree scan only; excludes Git history and external secret stores. Matches are not confirmed leaks.')
    report['totals'] = stats


def dry_run(root: Path, report: dict):
    required = ['docker-compose.yml', 'Makefile', 'run-all-omni.sh']
    missing = [x for x in required if not (root / x).is_file()]
    for x in required:
        record(report, 'prerequisite/' + x, 'fail' if x in missing else 'pass',
               'Missing file' if x in missing else 'Present; no execution performed')
    for x in ('run-all-omni.sh', 'verify-omni.sh'):
        file = root / x
        if file.exists():
            record(report, 'shell/' + x, 'pass' if os.access(file, os.X_OK) else 'warning',
                   'Executable' if os.access(file, os.X_OK) else 'Not executable; fix file mode before manual run')
    makefile = root / 'Makefile'
    if makefile.exists():
        targets = sorted(set(re.findall(r'(?m)^([A-Za-z_][\w-]*):(?:\s|$)', bounded_text(makefile))))
        report['make_targets'] = targets
    compose = root / 'docker-compose.yml'
    if compose.exists():
        try:
            response = subprocess.run(['docker', 'compose', '-f', str(compose), 'config', '--services',
                                       '--no-interpolate'], cwd=root, capture_output=True, timeout=20)
            if response.returncode == 0:
                report['compose_services'] = response.stdout.decode(errors='replace').splitlines()[:100]
                record(report, 'compose/list-services', 'pass', 'Compose service names enumerated without building or starting them')
            else:
                record(report, 'compose/list-services', 'warning',
                       'Compose validation unavailable, possibly due to unconfigured environment')
        except (OSError, subprocess.TimeoutExpired):
            record(report, 'compose/list-services', 'warning', 'Docker Compose unavailable or timed out')
    record(report, 'deployment', 'info', 'Nothing was built, pushed, deployed, restarted, or provisioned')
    report['totals'] = {'required_files': len(required), 'missing_required': len(missing),
                        'make_targets': len(report.get('make_targets', []))}


def save_report(report: dict, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    report['status'] = 'failed' if report['errors'] else ('warning' if report['warnings'] else 'passed')
    (output / 'operator-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = [f"# Operator report: {report['action']}", '',
             f"**Status:** {report['status']}",
             f"**Generated:** {report['generated_at_utc']}", '', '## Totals', '']
    lines.extend(f"- **{k}:** {v}" for k, v in report['totals'].items())
    lines += ['', '## Findings', '']
    for item in report['checks']:
        lines.append(f"- **{item['status'].upper()}** `{item['name']}` — {item['detail']}")
    if report['notes']:
        lines += ['', '## Scope', '']
        lines.extend('- ' + n for n in report['notes'])
    (output / 'operator-report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as fh:
            fh.write('\n'.join(lines[:15]) + '\n')
    print(f"Operator action {report['action']}: {report['status']}; checks={len(report['checks'])}; warnings={len(report['warnings'])}; errors={len(report['errors'])}")
    print(f"Full sanitized reports: {output}/operator-report.md and operator-report.json")
    return 1 if report['errors'] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate-all', 'inventory-report',
                                           'check-external-repos', 'security-scan', 'dry-run-deploy'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, default=Path('operator-report'))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = fresh_report(args.action)
    actions = {'validate-all': validate_all, 'inventory-report': inventory_report,
               'check-external-repos': external_repos, 'security-scan': security_scan,
               'dry-run-deploy': dry_run}
    try:
        actions[args.action](root, report)
    except Exception as exc:
        # Do not write traceback or raw data to Actions logs.
        record(report, 'operator_unhandled_exception', 'fail',
               'Check aborted: ' + type(exc).__name__ + ' (details suppressed)')
    return save_report(report, args.output)


if __name__ == '__main__':
    sys.exit(main())
