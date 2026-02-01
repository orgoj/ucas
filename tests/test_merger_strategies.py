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
        Simulates a real sandwich merge: System -> Mod -> Project Override.
        """
        from ucas.yaml_parser import parse_yaml
        fixtures_dir = Path(__file__).parent / "fixtures" / "practical_merge"
        
        # 1. Load System Base
        sys_cfg = parse_yaml((fixtures_dir / "system" / "ucas.yaml").read_text())
        
        # 2. Merge Mod (mod-git)
        mod_cfg = parse_yaml((fixtures_dir / "mods" / "mod-git" / "ucas.yaml").read_text())
        result = _merge_dicts(sys_cfg, mod_cfg, False, "mod")
        
        # 3. Merge Project Override
        prj_ovr_cfg = parse_yaml((fixtures_dir / "project" / ".ucas" / "ucas-override.yaml").read_text())
        result = _merge_dicts(result, prj_ovr_cfg, False, "override")
        
        # VERIFICATION
        self.assertEqual(result['requested_model'], 'claude-3-opus')
        self.assertIn('/usr/share/ucas/skills', result['skills'])
        self.assertIn('/opt/ucas/mods/git/skills', result['skills'])
        self.assertEqual(result['hooks']['prerun'], ['git pull'])
        self.assertEqual(result['new_feature'], 'enabled')
        self.assertNotIn('existing_feature', result)

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
