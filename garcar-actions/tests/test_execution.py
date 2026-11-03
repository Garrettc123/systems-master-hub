import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from garcar_actions.execution import execute
from garcar_actions.engine import job_environment


class ExecutionTests(unittest.TestCase):
    def run_script(self, script, directory, **limits):
        return execute([sys.executable, "-c", script], cwd=directory,
                       env=job_environment(directory), **limits)

    def test_output_quota_stops_noisy_child_and_bounds_retained_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script("import os\nwhile True: os.write(1, b'x'*8192)",
                                     directory, output_limit=16384, tail_bytes=512, timeout=3)
        self.assertEqual(result.returncode, 125)
        self.assertIn("OUTPUT_LIMIT", result.output)
        self.assertLess(len(result.output), 600)

    def test_timeout_kills_same_group_descendant(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "leaked.txt"
            # A missed descendant would create this marker after the timeout.
            child = "import pathlib,time;time.sleep(0.6);pathlib.Path('leaked.txt').write_text('leak')"
            script = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);time.sleep(5)"
            result = self.run_script(script, directory, timeout=0.2)
            time.sleep(0.7)
            self.assertFalse(marker.exists())
        self.assertEqual(result.returncode, 124)
        self.assertIn("TIMEOUT", result.output)

    def test_background_child_is_stopped_after_parent_success(self):
        with tempfile.TemporaryDirectory() as directory:
            child = "import pathlib,time;time.sleep(0.5);pathlib.Path('leaked.txt').write_text('leak')"
            script = f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child!r}]);print('done')"
            result = self.run_script(script, directory, timeout=2)
            time.sleep(0.6)
            self.assertFalse((Path(directory) / "leaked.txt").exists())
        self.assertEqual(result.returncode, 0)
        self.assertIn("done", result.output)

    def test_invalid_utf8_does_not_leave_job_unfinished(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script("import os;os.write(1,b'\\xffdone')", directory, timeout=2)
        self.assertEqual(result.returncode, 0)
        self.assertIn("done", result.output)
