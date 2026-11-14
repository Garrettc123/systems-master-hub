#!/usr/bin/env python3
"""Garcar external GitHub Actions alternative, without GitHub Actions runners.

Runs bounded repository inspections using the trusted local operator_manual.py;
no checkouts of untrusted submodules, no deployment, no secrets in reports,
and no remote mutation unless --publish-status is explicitly requested.

Python 3.11+. PyYAML required for `validate-all`; Git only for --repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ACTIONS = ('validate-all', 'inventory-report', 'check-external-repos',
           'security-scan', 'dry-run-deploy')
REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
REF = re.compile(r'[A-Za-z0-9][A-Za-z0-9_./-]*\Z')
SHA = re.compile(r'[a-f0-9]{40}\Z')


def repository_name(value: str) -> str:
    if not REPO.fullmatch(value) or any(part.startswith(('.', '-')) or part.endswith(('.', '-'))
                                             for part in value.split('/')):
        raise ValueError('Repository must be owner/name')
    return value


def git_ref(value: str) -> str:
    if not REF.fullmatch(value) or ('..' in value or '//' in value or '@{' in value
                                    or value.endswith(('/', '.', '.lock'))):
        raise ValueError('Invalid branch or tag')
    return value


def git_info(root: Path) -> dict:
    result = {'git_sha': None, 'dirty': None}
    for label, args in [('git_sha', ['rev-parse', 'HEAD']),
                        ('dirty', ['status', '--porcelain', '--untracked-files=no'])]:
        try:
            p = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                               text=True, check=False, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if p.returncode == 0:
            if label == 'git_sha' and SHA.fullmatch(p.stdout.strip()):
                result['git_sha'] = p.stdout.strip()
            elif label == 'dirty':
                result['dirty'] = bool(p.stdout.strip())
    return result


def clone_public_repo(repo: str, ref: str, target: Path) -> None:
    # A public clone only. No secret-bearing URLs, submodules, or git hooks.
    cmd = ['git', '-c', 'protocol.file.allow=never', '-c', 'credential.helper=', 'clone', '--depth', '1',
           '--single-branch', '--no-tags', '--branch', ref,
           'https://github.com/' + repo + '.git', str(target)]
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=180, check=False,
                       env={'PATH': os.environ.get('PATH', os.defpath),
                            'HOME': '/nonexistent',
                            'GIT_TERMINAL_PROMPT': '0',
                            'GIT_CONFIG_NOSYSTEM': '1',
                            'GIT_CONFIG_GLOBAL': os.devnull})
    if p.returncode != 0:
        raise RuntimeError('Public repository clone failed; check network, ref and access')


def report_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def execute(root: Path, output: Path, actions: tuple[str, ...], *,
            permit_network: bool = False, run_tests: bool = False) -> dict:
    script = Path(__file__).resolve().with_name('operator_manual.py')
    if not script.is_file():
        raise ValueError('Trusted operator_manual.py missing next to fallback runner')
    entries = []
    for action in actions:
        folder = output / action
        # Pass only the legacy operator its required context; hide GH_TOKEN unless
        # the operator was explicitly authorized to check remote repo access.
        env = os.environ.copy()
        if action != 'check-external-repos' or not permit_network:
            env.pop('GH_TOKEN', None)
        try:
            p = subprocess.run([sys.executable, str(script), action, '--root',
                                str(root), '--output', str(folder)], capture_output=True,
                               timeout=300, env=env, check=False)
            file = folder / 'operator-report.json'
            if not file.is_file():
                entry = {'action': action, 'status': 'failed', 'exit_code': p.returncode,
                         'reason': 'Report missing (details withheld)'}
            else:
                data = json.loads(file.read_text(encoding='utf-8'))
                status = data.get('status')
                if status not in ('passed', 'warning', 'failed'):
                    status = 'failed'
                if p.returncode and status != 'failed':
                    status = 'failed'
                entry = {'action': action, 'status': status, 'exit_code': p.returncode,
                         'checks': len(data.get('checks', [])),
                         'warnings': len(data.get('warnings', [])),
                         'errors': len(data.get('errors', [])),
                         'report_sha256': report_sha(file)}
        except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
            entry = {'action': action, 'status': 'failed',
                     'reason': 'Operator process failed (details withheld)'}
        entries.append(entry)
    if run_tests:
        test_path = Path(__file__).resolve().parents[1] / 'tests'
        # Executes only vetted local fallback tests, never tests from the
        # checked-out remote repository.
        try:
            p = subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                                '-s', str(test_path), '-p', 'test_operator_*.py'],
                               cwd=script.parents[1], capture_output=True,
                               timeout=120, check=False,
                               env={k: v for k, v in os.environ.items() if k != 'GH_TOKEN'})
            entries.append({'action': 'trusted-runner-tests',
                            'status': 'passed' if p.returncode == 0 else 'failed',
                            'exit_code': p.returncode})
        except (OSError, subprocess.TimeoutExpired):
            entries.append({'action': 'trusted-runner-tests', 'status': 'failed'})
    overall = 'failed' if any(e['status'] == 'failed' for e in entries) else (
        'warning' if any(e['status'] == 'warning' for e in entries) else 'passed')
    return {'schema': 'garcar.external-ci.v1',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': overall, 'actions': entries, 'git': git_info(root),
            'owner_approved_financial_actions': False,
            'deployed': False, 'live_payment_verified': False,
            'warning': ('External local evidence only; it does not replace a GitHub-hosted '
                        'required check or certify a production deployment.')}


def write_manifest(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'fallback-manifest.json'
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    lines = ['# Garcar External CI Fallback', '',
             '**Result:** ' + report['status'].upper(),
             '**Created:** ' + report['generated_at_utc'],
             '**Commit:** ' + str(report['git'].get('git_sha') or 'not confirmed'),
             '', '| Action | Status | Errors | Warnings |', '|---|---|---:|---:|']
    for entry in report['actions']:
        lines.append('| {action} | {status} | {errors} | {warnings} |'.format(
            action=entry['action'], status=entry['status'],
            errors=entry.get('errors', '—'), warnings=entry.get('warnings', '—')))
    lines += ['', 'Each check has a separate `operator-report.json` and Markdown report.',
              'No workflows were dispatched. No deployments, trades, sales emails, '
              'or transfers were executed.', '',
              'This is operator evidence, not a GitHub Actions green check.']
    (output / 'fallback-summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    evidence = {}
    for p in sorted(output.rglob('*')):
        if p.is_file() and p.name != 'fallback-checksums.json':
            evidence[p.relative_to(output).as_posix()] = report_sha(p)
    (output / 'fallback-checksums.json').write_text(
        json.dumps({'algorithm': 'sha256', 'files': evidence,
                    'note': 'Self-consistency only; files are not remotely anchored.'},
                   indent=2, sort_keys=True) + '\n', encoding='utf-8')


def publish_status(repo: str, sha: str, report: dict) -> dict:
    """Optional explicit GitHub status publication, never called by default.

    Requires fine-grained GH_TOKEN with Commit statuses: write. This status is
    distinct from GitHub Actions and cannot assert its checks passed.
    """
    token = os.environ.get('GH_TOKEN')
    if not token:
        return {'sent': False, 'reason': 'GH_TOKEN not configured'}
    if not SHA.fullmatch(sha):
        return {'sent': False, 'reason': 'Validated commit SHA unavailable'}
    state = 'success' if report['status'] == 'passed' else (
        'failure' if report['status'] == 'failed' else 'pending')
    payload = json.dumps({
        'state': state, 'context': 'garcar/external-operator',
        'description': ('External read-only operator audit: ' + report['status'])[:140],
    }).encode()
    url = 'https://api.github.com/repos/' + repo + '/statuses/' + sha
    request = Request(url, data=payload, method='POST', headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'Garcar-External-Operator/1.0'})
    try:
        with urlopen(request, timeout=12) as response:
            return {'sent': response.status == 201, 'http_status': response.status,
                    'context': 'garcar/external-operator'}
    except (HTTPError, URLError, OSError):
        return {'sent': False, 'reason': 'GitHub status API unavailable or not authorized'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--repository', type=repository_name,
                        help='Optional PUBLIC GitHub owner/name to clone read-only')
    parser.add_argument('--ref', type=git_ref, default='main')
    parser.add_argument('--actions', default='all',
                        help='all or comma-separated subset of five operator actions')
    parser.add_argument('--output', type=Path, default=Path.cwd() / 'operator-evidence')
    parser.add_argument('--network-repo-checks', action='store_true',
                        help='Allow gh CLI network checks with an existing GH_TOKEN')
    parser.add_argument('--trusted-tests', action='store_true',
                        help='Run only the bundled operator unit tests')
    parser.add_argument('--publish-status', action='store_true',
                        help='Post separate external result to GitHub; requires GH_TOKEN')
    args = parser.parse_args(argv)
    actions = ACTIONS if args.actions == 'all' else tuple(x.strip() for x in args.actions.split(','))
    if not actions or len(actions) != len(set(actions)) or any(x not in ACTIONS for x in actions):
        parser.error('Invalid actions; use all or unique comma-separated operator choices')
    if args.publish_status and not args.repository:
        parser.error('Status publishing requires --repository owner/name')
    output = args.output.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix='garcar-external-ci-') as work:
        try:
            if args.repository:
                root = Path(work) / 'source'
                clone_public_repo(args.repository, args.ref, root)
            else:
                root = args.root.expanduser().resolve(strict=True)
                if not root.is_dir():
                    raise ValueError('Repository root is not a directory')
            # Check while reports live outside the inspected source tree.
            scratch = Path(work) / 'reports'
            report = execute(root, scratch, actions,
                             permit_network=args.network_repo_checks,
                             run_tests=args.trusted_tests)
            report['repository'] = args.repository
            report['source_ref'] = args.ref if args.repository else None
            if args.publish_status:
                report['status_publish'] = publish_status(args.repository, report['git']['git_sha'], report)
            # Only write output once all repo inspection is complete.
            if output.is_relative_to(root) and output == root:
                raise ValueError('Output cannot replace repository root')
            if output.exists() and output.is_symlink():
                raise ValueError('Output must not be a symlink')
            shutil.copytree(scratch, output, dirs_exist_ok=True)
            write_manifest(output, report)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            print('Fallback run aborted; check repo/ref/path and network permissions.', file=sys.stderr)
            return 2
    print('Garcar external CI: ' + report['status'] + '; reports=' + str(output))
    return 1 if report['status'] == 'failed' else 0


if __name__ == '__main__':
    sys.exit(main())