#!/usr/bin/env python3
"""Read-only scheduled GitHub Actions-independent operator validation.

Executes trusted github_ci_fallback.py against a public GitHub branch;
does not merge, deploy, transfer funds, send mail, or rotate credentials.
Requires Python 3.11+, git and PyYAML (for YAML validation).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from github_ci_fallback import repository_name, git_ref

SHA = re.compile(r'[a-f0-9]{40}\Z')


def head_sha(repo: str, branch: str) -> str:
    """Resolve the named public branch without shell or stored credentials."""
    repo, branch = repository_name(repo), git_ref(branch)
    env = {'PATH': os.defpath, 'HOME': '/nonexistent',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': os.devnull}
    p = subprocess.run(['git', '-c', 'credential.helper=', 'ls-remote',
                        '--exit-code', 'https://github.com/' + repo + '.git',
                        'refs/heads/' + branch], capture_output=True,
                       timeout=35, check=False, env=env)
    if p.returncode:
        raise RuntimeError('GitHub branch could not be verified')
    lines = p.stdout.decode('ascii', errors='replace').strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError('Unexpected GitHub branch response')
    parts = lines[0].split('\t')
    if len(parts) != 2 or parts[1] != 'refs/heads/' + branch or not SHA.fullmatch(parts[0]):
        raise RuntimeError('Invalid GitHub revision response')
    return parts[0]


def _read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else None
    except (OSError, UnicodeError, ValueError):
        return None


def _atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n',
                   encoding='utf-8')
    os.replace(tmp, path)


def one_cycle(repo: str, branch: str, destination: Path, *, force=False,
              trusted_tests=True, publisher=False, discover=head_sha) -> dict:
    """Run on a changed public branch revision, persisting evidence per SHA."""
    destination.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    state_path = destination / 'supervisor-state.json'
    previous = _read_json(state_path) or {}
    try:
        remote_sha = discover(repo, branch)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        failure = {'status': 'network_error', 'reason': type(exc).__name__,
                   'checked_at_utc': now, 'repository': repo, 'branch': branch,
                   'remote_sha_verified': False, 'validation_executed': False}
        _atomic_json(state_path, failure)
        return failure
    if not force and previous.get('remote_sha') == remote_sha and (
            previous.get('last_validated_status') in ('passed', 'warning')):
        reused = dict(previous)
        reused.update(status='unchanged', checked_at_utc=now,
                      validation_executed=False, remote_sha_verified=True)
        _atomic_json(state_path, reused)
        return reused
    folder = destination / remote_sha
    folder.mkdir(exist_ok=True)
    runner = Path(__file__).resolve().with_name('github_ci_fallback.py')
    cmd = [sys.executable, str(runner), '--repository', repo, '--ref', branch,
           '--actions', 'all', '--output', str(folder)]
    if trusted_tests:
        cmd.append('--trusted-tests')
    if publisher:
        cmd.append('--publish-status')
    # Do not pass Stripe, Supabase, cloud or personal credentials to inspections.
    env = {'PATH': os.environ.get('PATH', os.defpath),
           'HOME': os.environ.get('HOME', '/nonexistent'),
           'LANG': 'C.UTF-8', 'PYTHONUNBUFFERED': '1',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': os.devnull}
    if publisher and os.environ.get('GH_TOKEN'):
        env['GH_TOKEN'] = os.environ['GH_TOKEN']
    try:
        p = subprocess.run(cmd, timeout=900, capture_output=True,
                           check=False, env=env)
        evidence = _read_json(folder / 'fallback-manifest.json')
        git = (evidence or {}).get('git')
        observed_sha = git.get('git_sha') if isinstance(git, dict) else None
        status = (evidence or {}).get('status')
        if p.returncode not in (0, 1) or status not in ('passed', 'warning', 'failed'):
            status = 'failed'
        if observed_sha != remote_sha:
            status = 'revision_mismatch'
        if p.returncode == 1 and status != 'failed':
            status = 'failed'
        report_file = folder / 'fallback-manifest.json'
        digest = hashlib.sha256(report_file.read_bytes()).hexdigest() if report_file.is_file() else None
    except (OSError, subprocess.TimeoutExpired):
        status, observed_sha, digest = 'failed', None, None
    result = {'status': status, 'checked_at_utc': now, 'repository': repo,
              'branch': branch, 'remote_sha': remote_sha,
              'observed_sha': observed_sha, 'remote_sha_verified': True,
              'validation_executed': True, 'last_validated_status': status,
              'report_relative_path': remote_sha + '/fallback-manifest.json' if digest else None,
              'report_sha256': digest,
              'live_payment_verified': False, 'production_deployed': False}
    _atomic_json(state_path, result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='Garrettc123/systems-master-hub',
                        type=repository_name)
    parser.add_argument('--branch', default='fix/operator-manual-audit-20261106',
                        type=git_ref)
    parser.add_argument('--output', type=Path, default=Path('operator-evidence-supervised'))
    parser.add_argument('--interval-seconds', type=int, default=3600)
    parser.add_argument('--max-cycles', type=int, default=1,
                        help='0 = continuous')
    parser.add_argument('--force', action='store_true',
                        help='Rerun even if revision is unchanged')
    parser.add_argument('--no-trusted-tests', action='store_true')
    parser.add_argument('--publish-status', action='store_true',
                        help='Explicit authorized GitHub commit status write')
    args = parser.parse_args(argv)
    if args.interval_seconds < 300 or args.max_cycles < 0:
        parser.error('Interval must be >= 300 seconds and max-cycles >= 0')
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.supervisor.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Supervisor already running for this output', file=sys.stderr)
            return 2
        n = 0
        result = {'status': 'network_error'}
        while args.max_cycles == 0 or n < args.max_cycles:
            result = one_cycle(args.repository, args.branch, output,
                               force=args.force,
                               trusted_tests=not args.no_trusted_tests,
                               publisher=args.publish_status)
            print(json.dumps({k: result.get(k) for k in (
                'status', 'checked_at_utc', 'remote_sha', 'validation_executed')},
                sort_keys=True), flush=True)
            n += 1
            if args.max_cycles == 0 or n < args.max_cycles:
                time.sleep(args.interval_seconds)
        return 1 if result['status'] in (
            'failed', 'revision_mismatch', 'network_error') else 0


if __name__ == '__main__':
    sys.exit(main())
