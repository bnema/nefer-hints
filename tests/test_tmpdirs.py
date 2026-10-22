"""Data-free scratch directory ownership and capture environment checks."""
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from train.tmpdirs import capture_env, private_dir


class ScratchTests(unittest.TestCase):
    def test_private_mode_and_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'scratch'
            self.assertEqual(private_dir(path), path)
            path.chmod(0o755)
            private_dir(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)

    def test_reject_symlink_file_and_foreign_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'link').symlink_to(base, target_is_directory=True)
            (base / 'file').write_text('')
            for name in ('link', 'file'):
                with self.subTest(name=name), self.assertRaisesRegex(SystemExit, 'Unsafe scratch'):
                    private_dir(base / name)
            foreign = base.stat()
            with patch('train.tmpdirs.os.getuid', return_value=foreign.st_uid + 1):
                with self.assertRaisesRegex(SystemExit, 'not an owned directory'):
                    private_dir(base)

    def test_environment_allowlist_and_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'SSH_AUTH_SOCK': '/secret', 'DISPLAY': ':0',
                                         'DBUS_SESSION_BUS_ADDRESS': 'secret'}):
                env = capture_env(Path(tmp) / 'home')
            self.assertEqual(set(env), {'PATH', 'LANG', 'HOME', 'XDG_CONFIG_HOME',
                                       'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME',
                                       'XDG_RUNTIME_DIR'})
            self.assertEqual(stat.S_IMODE(Path(env['XDG_RUNTIME_DIR']).stat().st_mode), 0o700)
