import io
import os
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from ucas.__main__ import list_agents, list_teams


class TestListCommands(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.project_root = self.test_dir / "project"
        self.project_root.mkdir()
        self.project_mods = self.project_root / ".ucas" / "mods"
        self.project_mods.mkdir(parents=True)

        self.old_cwd = Path.cwd()
        os.chdir(self.project_root)

        # Isolation: mock user/system layers away from host
        self.home_patcher = unittest.mock.patch('pathlib.Path.home', return_value=self.test_dir)
        self.home_patcher.start()
        self.env_patcher = unittest.mock.patch.dict(os.environ, {"UCAS_HOME": ""})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        self.home_patcher.stop()
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def _create_mod(self, name: str, config_content: str):
        mod_dir = self.project_mods / name
        mod_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "ucas.yaml").write_text(config_content)
        return mod_dir

    def test_list_agents_and_teams(self):
        # Agent
        self._create_mod("agent1", "name: agent1\n")
        # Team definition
        self._create_mod("team1", "team:\n  name: team1\n  agents:\n    a: agent1\n")
        # ACLI mod
        self._create_mod("acli-test", "acli:\n  executable: test-cli\n")
        # Run mod
        self._create_mod("run-test", "run:\n  template: echo {cmd}\n")

        with unittest.mock.patch("sys.stdout", new=io.StringIO()) as buf:
            list_agents()
            agents_out = buf.getvalue().strip().splitlines()

        with unittest.mock.patch("sys.stdout", new=io.StringIO()) as buf:
            list_teams()
            teams_out = buf.getvalue().strip().splitlines()

        self.assertIn("agent1", agents_out)
        self.assertNotIn("team1", agents_out)
        self.assertNotIn("acli-test", agents_out)
        self.assertNotIn("run-test", agents_out)

        self.assertIn("team1", teams_out)
        self.assertNotIn("agent1", teams_out)


if __name__ == "__main__":
    unittest.main()
