"""Browser-free regression tests for collection domain exclusions."""
import unittest
from urllib.parse import urlparse
from unittest.mock import patch

from train.web.collect_web import (blocked_domains, excluded, blocked, task_key,
                                   task_id, merge_results, env_for)


class ExclusionTests(unittest.TestCase):
    def test_exact_host(self):
        self.assertTrue(excluded('github.com', {'github.com'}))

    def test_subdomain(self):
        self.assertTrue(excluded('docs.github.com', {'github.com'}))

    def test_lookalike(self):
        for host in ('notgithub.com', 'github.com.example.org'):
            with self.subTest(host=host):
                self.assertFalse(excluded(host, {'github.com'}))

    def test_normalization(self):
        for host, domain in (('WWW.GitHub.COM.', 'github.com'),
                             ('github.com', 'WWW.GITHUB.COM.'),
                             ('Docs.GitHub.Com.', 'www.github.com')):
            with self.subTest(host=host, domain=domain):
                self.assertTrue(excluded(host, {domain}))

    def test_redirect_to_excluded_host(self):
        planned_url = 'https://allowed.example/page'
        final_url = 'https://www.github.com/login'
        domains = {'github.com'}
        self.assertFalse(excluded(urlparse(planned_url).hostname, domains))
        self.assertTrue(excluded(urlparse(final_url).hostname, domains))

    def test_scene_hosts_extend_existing_exclusions(self):
        with patch('pathlib.Path.read_text', return_value=
                   '{"new": {"url": "https://WWW.NEW-EVAL.EXAMPLE./page"}}'):
            domains = blocked_domains()
        self.assertTrue(excluded('new-eval.example', domains))
        self.assertTrue(excluded('github.com', domains))
        self.assertFalse(excluded('allowed.example', domains))


class ResumeTests(unittest.TestCase):
    def test_legacy_and_explicit_ids(self):
        self.assertEqual(task_id({'site': 'gtk'}, 7), 'gtk_0007')
        self.assertEqual(task_id({'site': 'gtk', 'id': 'gtk_hash'}, 999), 'gtk_hash')

    def test_task_identity_ignores_bookkeeping(self):
        task = dict(url='https://example.org', scroll='top', zoom=100,
                    dark=False, size='1920x1080')
        self.assertEqual(task_key(task), task_key(dict(task, id='old', v=2)))
        self.assertNotEqual(task_key(task), task_key(dict(task, zoom=90)))

    def test_merge_preserves_legacy_success_and_history(self):
        old = [{'id': 'old', 'boxes': 4}, {'id': 'retry', 'ok': False},
               {'error': 'legacy diagnostic'}]
        merged = merge_results(old, [{'id': 'old', 'ok': False},
                                     {'id': 'retry', 'ok': True},
                                     {'id': 'new', 'ok': True}])
        self.assertIn(old[0], merged)
        self.assertIn(old[2], merged)
        self.assertIn({'id': 'retry', 'ok': True}, merged)
        self.assertEqual(len(merged), 4)

    def test_recovery_cannot_revive_quality_rejection(self):
        old = [{'id': 'bad', 'quality_rejected': True, 'ok': False}]
        self.assertEqual(merge_results(old, [{'id': 'bad', 'ok': True}]), old)

    def test_browser_error_and_challenge_filters(self):
        for title in ('Just a moment', "This site can’t be reached", 'Access denied'):
            self.assertTrue(blocked(title, ''))
        self.assertFalse(blocked('Forms · Bootstrap', 'Email address Password'))

    def test_fake_home_is_recreated(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            with patch('train.web.collect_web.FAKE', Path(tmp) / 'missing'):
                env = env_for('web0')
                self.assertTrue(Path(env['HOME']).is_dir())
                self.assertTrue(Path(env['XDG_CONFIG_HOME']).is_dir())
                self.assertNotIn('NEFERWL', env)


if __name__ == '__main__':
    unittest.main()
