"""Bounded command capture for reviewed-code POSIX canaries, not an OS sandbox."""
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    returncode: int
    output: str


def execute(argv, *, cwd, env, timeout=600, output_limit=1_048_576, tail_bytes=12_000):
    """Stop on timeout/output quota; retain only a bounded tail in memory.

    Children remaining in the command's POSIX process group are killed on exit.
    Code that changes its session/group can escape this mechanism; use a job
    container or VM before running untrusted code.
    """
    if os.name != "posix":
        raise OSError("The canary worker requires a POSIX host")
    if timeout <= 0 or output_limit <= 0 or tail_bytes <= 0:
        raise ValueError("Execution limits must be positive")
    tail = bytearray()
    total = 0
    forced_code = None
    reason = ""
    deadline = time.monotonic() + timeout
    with subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          shell=False, start_new_session=True, close_fds=True,
                          bufsize=0) as process:
        def stop_group():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map() or process.poll() is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        forced_code, reason = 124, "TIMEOUT: execution deadline exceeded"
                        break
                    # Clean up background processes even after a successful parent exits.
                    if process.poll() is not None:
                        stop_group()
                    for key, _ in selector.select(min(remaining, 0.05)):
                        chunk = os.read(key.fd, 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        total += len(chunk)
                        tail.extend(chunk)
                        del tail[:-tail_bytes]
                        if total > output_limit:
                            forced_code, reason = 125, "OUTPUT_LIMIT: output quota exceeded"
                            break
                    if forced_code is not None:
                        break
                    if not selector.get_map() and process.poll() is None:
                        time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        finally:
            stop_group()
            process.wait(timeout=5)
            process.stdout.close()
    output = tail.decode("utf-8", errors="replace")
    if reason:
        output += "\n" + reason
    return Result(forced_code if forced_code is not None else process.returncode, output)
