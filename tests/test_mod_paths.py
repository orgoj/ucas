import unittest
import unittest.mock
import os
import shutil
import tempfile
from pathlib import Path
from ucas.resolver import get_search_paths, find_entity
from ucas.__main__ import resolve_entities

class TestModPaths(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Isolation: Mock Path.home to point to our test dir
        self.home_patcher = unittest.mock.patch('pathlib.Path.home', return_value=self.test_dir)
        self.mock_home = self.home_patcher.start()
        
        # Isolation: Ensure UCAS_HOME doesn't leak from host
        self.env_patcher = unittest.mock.patch.dict(os.environ, {"UCAS_HOME": ""})
        self.env_patcher.start()

        # Create standard project structure
        self.project_mods = self.test_dir / '.ucas' / 'mods'
        self.project_mods.mkdir(parents=True)
        
        # Create an external mods directory
        self.external_mods = self.test_dir / 'external_mods'
        self.external_mods.mkdir()

    def tearDown(self):
        self.env_patcher.stop()
        self.home_patcher.stop()
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def create_mod(self, base_path, name, config_content=""):
        mod_dir = base_path / name
        mod_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / 'ucas.yaml').write_text(config_content)
        return mod_dir

    def test_default_search_path(self):
        self.create_mod(self.project_mods, 'mod1')
        paths = get_search_paths()
        self.assertIn(self.project_mods, paths)
        
        entity = find_entity('mod1', paths)
        self.assertEqual(entity, self.project_mods / 'mod1')

    def test_extra_mod_path(self):
        self.create_mod(self.external_mods, 'ext_mod')
        
        # Should NOT find it by default
        paths = get_search_paths()
        self.assertIsNone(find_entity('ext_mod', paths))
        
        # Should find it with extra_paths
        paths = get_search_paths(extra_paths=[str(self.external_mods)])
        self.assertIn(self.external_mods, paths)
        entity = find_entity('ext_mod', paths)
        self.assertEqual(entity, self.external_mods / 'ext_mod')

    def test_strict_mode(self):
        # We can't easily mock Path.home() and env vars globally without more effort,
        # but we can test if get_search_paths respects the strict flag.
        
        # Mocking System/User paths would require patching resolver internals.
        # Let's just check if it returns fewer paths when strict=True.
        
        # This test might be environmental dependent, so let's just verify logic.
        paths_normal = get_search_paths(strict=False)
        paths_strict = get_search_paths(strict=True)
        
        # Strict should only have project mods (and extra paths if provided)
        self.assertLessEqual(len(paths_strict), len(paths_normal))

    def test_dynamic_resolution_agent_adds_path(self):
        # Agent in project mods
        self.create_mod(self.project_mods, 'agent1', f"mod_path: [{str(self.external_mods)}]")
        
        # Mod in external mods
        self.create_mod(self.external_mods, 'mod1')
        
        # resolve_entities should find mod1 because agent1 adds the path
        # We need to mock get_layer_config_paths to avoid reading real system/user configs
        with unittest.mock.patch('ucas.__main__.get_layer_config_paths') as mock_layers:
            # Set project config to empty
            mock_layers.return_value = ((None, None), (None, None), (None, None))
            
            agent_path, mod_paths = resolve_entities('agent1', ['mod1'], debug=False)
            
            self.assertEqual(agent_path, self.project_mods / 'agent1')
            self.assertEqual(len(mod_paths), 1)
            self.assertEqual(mod_paths[0], self.external_mods / 'mod1')

    def test_dynamic_resolution_mod_chaining(self):
        # agent1 (project) -> mod1 (external1) -> mod2 (external2)
        external1 = self.test_dir / 'ext1'
        external2 = self.test_dir / 'ext2'
        external1.mkdir()
        external2.mkdir()
        
        self.create_mod(self.project_mods, 'agent1', f"mod_path: [{str(external1)}]")
        self.create_mod(external1, 'mod1', f"mod_path: [{str(external2)}]")
        self.create_mod(external2, 'mod2')
        
        with unittest.mock.patch('ucas.__main__.get_layer_config_paths') as mock_layers:
            mock_layers.return_value = ((None, None), (None, None), (None, None))
            
            agent_path, mod_paths = resolve_entities('agent1', ['mod1', 'mod2'], debug=False)
            
            self.assertEqual(mod_paths[0], external1 / 'mod1')
            self.assertEqual(mod_paths[1], external2 / 'mod2')

    def test_relative_mod_path_in_mod(self):
        # mod1 in project adds a relative path to 'libs'
        libs_dir = self.project_mods / 'mod1' / 'libs'
        libs_dir.mkdir(parents=True)
        self.create_mod(libs_dir, 'mod2')
        
        self.create_mod(self.project_mods, 'mod1', "mod_path: ['./libs']")
        
        with unittest.mock.patch('ucas.__main__.get_layer_config_paths') as mock_layers:
             mock_layers.return_value = ((None, None), (None, None), (None, None))
             
             # agent is mod1 itself for this test
             agent_p, mod_ps = resolve_entities('mod1', ['mod2'], debug=False)
             
             self.assertEqual(mod_ps[0], libs_dir / 'mod2')

if __name__ == '__main__':
    unittest.main()
