import unittest
import subprocess
import os
import sys
from pathlib import Path

class TestUCASDryRun(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parent.parent.resolve()
        self.fixtures_dir = self.repo_root / "tests" / "fixtures"
        self.project_dir = self.fixtures_dir / "project"
        
        # Setup environment
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(self.repo_root)
        self.env["UCAS_HOME"] = str(self.fixtures_dir)
        # Session ID for stability in tests
        self.env["UCAS_SESSION_ID"] = "test-session"

    def run_ucas(self, cmd_args, cwd=None):
        if cwd is None:
            cwd = self.project_dir
        
        full_cmd = [sys.executable, "-m", "ucas"] + cmd_args + ["--dry-run"]
        result = subprocess.run(
            full_cmd,
            cwd=cwd,
            env=self.env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}", file=sys.stderr)
        return result

    def test_run_basic_agent(self):
        """Test running a single agent from the library."""
        res = self.run_ucas(["run", "basic-agent"])
        self.assertEqual(res.returncode, 0)
        # Expect export block + main command
        self.assertIn("export UCAS_AGENT=basic-agent", res.stdout)
        self.assertIn("test-exe", res.stdout)
        self.assertIn("--msg", res.stdout) # Prompt file flag

    def test_run_agent_with_mod(self):
        """Test agent + mod command chaining."""
        res = self.run_ucas(["run", "basic-agent", "+mod-a"])
        self.assertEqual(res.returncode, 0)
        # Should contain mod hook
        self.assertIn("MOD-A-PRE", res.stdout)
        # Should contain both in export
        self.assertIn("UCAS_AGENT=basic-agent", res.stdout)

    def test_run_team(self):
        """Test team execution from config."""
        res = self.run_ucas(["run-team", "test-team"])
        self.assertEqual(res.returncode, 0)
        # Check member execution
        self.assertIn("[member1] Command:", res.stdout)
        # Member should have team mod (mod-a) and its own mod (basic-agent)
        # The base agent name is basic-agent (resolved from mods[0])
        self.assertIn("export UCAS_TEAM=test-team", res.stdout)
        self.assertIn('echo "MOD-A-PRE"', res.stdout)
        self.assertIn("test-exe --msg", res.stdout)

if __name__ == "__main__":
    unittest.main()
