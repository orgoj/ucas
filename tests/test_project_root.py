import os
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from ucas.resolver import get_search_paths, find_entity
from ucas.merger import resolve_entities


class TestProjectRootPlumbing(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.project_root = self.test_dir / "project"
        self.project_root.mkdir()

        self.project_mods = self.project_root / ".ucas" / "mods"
        self.project_mods.mkdir(parents=True)

        self.old_cwd = Path.cwd()

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

    def _create_mod(self, base_path: Path, name: str, config_content: str = "") -> Path:
        mod_dir = base_path / name
        mod_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "ucas.yaml").write_text(config_content)
        return mod_dir

    def test_get_search_paths_with_project_root(self):
        self._create_mod(self.project_mods, "mod1")

        paths = get_search_paths(project_root=self.project_root)
        self.assertIn(self.project_mods, paths)
        self.assertEqual(find_entity("mod1", paths), self.project_mods / "mod1")

    def test_resolve_entities_with_project_root(self):
        # Ensure we are NOT in the project root
        os.chdir(self.test_dir)

        self._create_mod(self.project_mods, "agent1")
        self._create_mod(self.project_mods, "mod1")

        agent_path, mod_paths, _, _ = resolve_entities(
            "agent1",
            ["mod1"],
            project_root=self.project_root
        )

        self.assertEqual(agent_path, self.project_mods / "agent1")
        self.assertEqual(mod_paths[0], self.project_mods / "mod1")


if __name__ == "__main__":
    unittest.main()
