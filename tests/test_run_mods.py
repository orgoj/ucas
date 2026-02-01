import unittest
import os
import sys
from pathlib import Path
from ucas.launcher import expand_run_template, select_run_mod
from ucas.resolver import get_run_config

class TestRunMods(unittest.TestCase):
    def setUp(self):
        self.context = {
            'UCAS_AGENT': 'test-agent',
            'UCAS_TEAM': 'test-team',
            'UCAS_PROJECT_ROOT': '/home/user/project',
            'UCAS_SESSION_ID': 'test-session-uuid'
        }

    def test_expand_run_template(self):
        # Template expansion is now internal to launcher but we can still test the helper
        template = 'bash -c "{cmd}"'
        cmd = 'echo hello'
        expanded = expand_run_template(template, cmd, 'test-agent', self.context)
        self.assertEqual(expanded, 'bash -c "echo hello"')

    def test_get_run_args(self):
        from ucas.launcher import get_run_args
        cmd = 'my-cmd'
        args = get_run_args(cmd, 'test-agent', self.context)
        
        # Check for key arguments
        self.assertIn('--cmd', args)
        self.assertIn('my-cmd', args)
        self.assertIn('--agent', args)
        self.assertIn('test-agent', args)
        self.assertIn('--session-name', args)
        self.assertIn('project-test-team', args)

    def test_select_run_mod_default(self):
        config = {
            'allowed_run': ['run-bash', 'run-tmux'],
            'default_run': 'run-bash'
        }
        res = select_run_mod(config)
        self.assertEqual(res, 'run-bash')

    def test_select_run_mod_override(self):
        config = {
            'allowed_run': ['run-bash', 'run-tmux'],
            'override_run': 'run-tmux'
        }
        res = select_run_mod(config)
        self.assertEqual(res, 'run-tmux')

    def test_select_run_mod_from_definition(self):
        # If the config itself is a run-mod definition
        config = {
            'run': {
                'name': 'my-custom-run',
                'template': 'custom {cmd}'
            }
        }
        res = select_run_mod(config)
        self.assertEqual(res, 'my-custom-run')

if __name__ == "__main__":
    unittest.main()
