"""Browser-free regression tests for collection domain exclusions."""
import unittest
from urllib.parse import urlparse
from unittest.mock import patch

from train.web.collect_web import blocked_domains, excluded


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


if __name__ == '__main__':
    unittest.main()
