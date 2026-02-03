import unittest
from pathlib import Path
from ucas.merger import _merge_dicts

class TestMergerStrategies(unittest.TestCase):
    def test_basic_overwrite(self):
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}
        expected = {"a": 1, "b": 3, "c": 4}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_merge_plus_list(self):
        base = {"l": ["a", "b"]}
        overlay = {"l+": ["c"]}
        expected = {"l": ["a", "b", "c"]}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_merge_plus_dict(self):
        base = {"d": {"a": 1}}
        overlay = {"d+": {"b": 2}}
        expected = {"d": {"a": 1, "b": 2}}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_remove_minus_list(self):
        base = {"l": ["a", "b", "c"]}
        overlay = {"l-": ["b"]}
        expected = {"l": ["a", "c"]}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_remove_minus_dict(self):
        base = {"d": {"a": 1, "b": 2}}
        overlay = {"d-": ["a"]}
        expected = {"d": {"b": 2}}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_override_bang(self):
        base = {"d": {"a": 1}}
        overlay = {"d!": {"b": 2}}
        expected = {"d": {"b": 2}}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_default_question(self):
        base = {"a": 1}
        overlay = {"a?": 2, "b?": 3}
        expected = {"a": 1, "b": 3}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_update_tilde(self):
        base = {"a": 1}
        overlay = {"a~": 2, "b~": 3}
        expected = {"a": 2}  # b is ignored because it doesn't exist in base
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_nested_strategies(self):
        base = {"outer": {"inner": [1, 2]}}
        overlay = {"outer+": {"inner+": [3]}}
        expected = {"outer": {"inner": [1, 2, 3]}}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_no_longer_auto_append(self):
        # skills, mods, and hooks should now OVERWRITE by default if no + suffix
        base = {"skills": ["s1"]}
        overlay = {"skills": ["s2"]}
        expected = {"skills": ["s2"]}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_mod_metadata_list_merge(self):
        # Testing the new mods+: [ {name: ...} ] pattern
        base = {"mods": ["run-bash"]}
        overlay = {"mods+": [{"name": "ucas", "description": "dev mod"}]}
        expected = {"mods": ["run-bash", {"name": "ucas", "description": "dev mod"}]}
        self.assertEqual(_merge_dicts(base, overlay, False, "test"), expected)

    def test_practical_onboarding_scenario(self):
        """
        Simulates a real sandwich merge: System -> Default Mod -> Agent -> Project Override.
        """
        from ucas.merger import merge_configs
        fixtures_dir = Path(__file__).parent / "fixtures" / "practical_merge"
        
        # We need to mock get_layer_config_paths to use our test fixtures
        import ucas.merger
        
        # Setup directories
        system_dir = fixtures_dir / "system"
        project_dir = fixtures_dir / "project"
        mods_dir = fixtures_dir / "mods"
        
        # Create a mock for get_layer_config_paths
        with unittest.mock.patch('ucas.merger.get_layer_config_paths') as mock_paths:
            # system_config, system_override, user_config, user_override, project_config, project_override
            mock_paths.return_value = (
                (system_dir / "ucas.yaml", None), # System
                (None, None),                    # User
                (None, project_dir / ".ucas" / "ucas-override.yaml") # Project Override
            )
            
            # Temporary agent dir
            agent_path = Path("/tmp/ucas-test-agent")
            agent_path.mkdir(parents=True, exist_ok=True)
            (agent_path / "ucas.yaml").write_text("requested_model: agent-model\n")
            
            default_mod_path = mods_dir / "mod-git"
            
            # Run merge: System -> Default Mod -> Agent -> Project Override
            result = merge_configs(
                agent_path=agent_path,
                default_mod_paths=[default_mod_path],
                explicit_mod_paths=[],
                debug=False
            )
            
            # VERIFICATION
            # 1. System defaults has requested_model: gpt-4
            # 2. Agent has requested_model: agent-model
            # 3. Project Override HAS requested_model!: claude-3-opus
            # The '!' suffix in override layer means it ALWAYS wins.
            self.assertEqual(result['requested_model'], 'claude-3-opus')
            
            # Project Override adds 'new_feature' and removes 'existing_feature'
            self.assertEqual(result['new_feature'], 'enabled')
            
            # Clean up
            import shutil
            shutil.rmtree(agent_path)

    def test_practical_team_override(self):
        """
        Test merging team definitions within a mod.
        """
        base_team = {
            "team": {
                "mods": ["global-mod"],
                "agents": {
                    "karel": ["chat"]
                }
            }
        }
        
        project_overlay = {
            "team+": {
                "agents+": {
                    "karel+": ["extra-mod"],
                    "lucie": ["chat", "aws-mod"]
                }
            }
        }
        
        result = _merge_dicts(base_team, project_overlay, False, "project")
        self.assertEqual(result['team']['agents']['karel'], ["chat", "extra-mod"])
        self.assertEqual(result['team']['agents']['lucie'], ["chat", "aws-mod"])
        self.assertEqual(result['team']['mods'], ["global-mod"])

if __name__ == '__main__':
    unittest.main()
