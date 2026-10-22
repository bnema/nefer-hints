"""Startup metadata lookup, validation and precedence over binary hello."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from protocol import ROOT


class ModelConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = Path(self.tmp.name)
        for source in (ROOT / 'models').glob('*.ncnn.*'):
            (self.model / source.name).symlink_to(source.resolve())

    def run_model(self, metadata, extra=(), model=None):
        (self.model / 'model.json').write_text(metadata)
        p = subprocess.run([str(ROOT / 'build/nefer-hints'), '--imgsz', '640',
                            '--gpu', 'cpu', *extra, '--model',
                            str(model or self.model)], input=b'',
                           capture_output=True, timeout=60)
        self.assertEqual(p.stdout[:4], b'NHNT')
        version, status, length = struct.unpack('<III', p.stdout[4:16])
        self.assertEqual(version, 1)
        message = p.stdout[16:16 + length].decode()
        self.assertTrue(message)
        self.assertEqual(p.returncode, status)
        return status, p.stderr.decode()

    def test_defaults_and_cli(self):
        metadata = json.dumps(dict(name='terminal-v1', conf=.075, iou=.4,
                                   ignored='value'))
        status, log = self.run_model(metadata)
        self.assertEqual(status, 0)
        self.assertIn('conf=0.075; iou=0.4; model=terminal-v1', log)
        status, log = self.run_model(metadata, ('--conf', '.2', '--iou', '.3'))
        self.assertEqual(status, 0)
        self.assertIn('conf=0.2; iou=0.3', log)
        # CLI after --model works too (the final --model is the same directory).
        status, log = self.run_model(metadata, ('--model', str(self.model), '--conf', '.9'))
        self.assertEqual(status, 0)
        self.assertIn('conf=0.9; iou=0.4', log)

    def test_prefix_lookup(self):
        prefix = self.model / 'icon_detect-640'
        for model in (prefix, Path(str(prefix) + '.ncnn.param')):
            status, log = self.run_model('{"conf":0.12}', model=model)
            self.assertEqual(status, 0)
            self.assertIn('conf=0.12; iou=0.7', log)
        Path(str(prefix) + '.json').write_text('{"iou":0.2}')
        status, log = self.run_model('{"conf":0.12}', model=prefix)
        self.assertEqual(status, 0)
        self.assertIn('conf=0.05; iou=0.2', log)

    def test_invalid(self):
        for metadata in ('{', '[]', '{"conf":0}', '{"conf":1.1}',
                         '{"iou":-0.1}', '{"iou":1.1}', '{"conf":NaN}',
                         '{"conf":1e999}', '{"name":1}', '{"conf":".1"}',
                         '{"conf":.1}', '{"conf":01}', '{"iou":0,}',
                         '{} trailing', '{"name":"\\q"}'):
            with self.subTest(metadata=metadata):
                status, _ = self.run_model(metadata, ('--conf', '.5'))
                self.assertEqual(status, 1)

    def test_empty_and_escaped_strings(self):
        status, log = self.run_model('{}')
        self.assertEqual(status, 0)
        self.assertIn('conf=0.05; iou=0.7', log)
        status, log = self.run_model('{"name":"terminal-\\u0076\\u0031", "iou":0, "conf":1}')
        self.assertEqual(status, 0)
        self.assertIn('conf=1; iou=0; model=terminal-v1', log)
