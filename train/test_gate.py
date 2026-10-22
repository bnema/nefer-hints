"""Data-free tests for validation selection and the unchanged TEST gate."""
import contextlib
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from train import gate


def metrics(**changes):
    return dict(web_only_precision=0.6, web_only_recall=0.7,
                native_precision=0.8, native_recall=0.9,
                web_precision=0.1, web_recall=0.1,
                terminal_fp_per_screen=1.0, terminal_recall=0.8, **changes)


class SelectTests(unittest.TestCase):
    def setUp(self):
        self.base = metrics()
        self.base['terminal_fp_per_screen'] = 5.0

    def test_boundaries_and_each_failure(self):
        ft = metrics()
        for key in ('web_only_recall', 'native_precision', 'native_recall'):
            ft[key] = self.base[key] - 0.02
        self.assertTrue(all(gate.check_select(self.base, ft).values()))
        for key in ('web_only_recall', 'native_precision', 'native_recall',
                    'terminal_recall', 'terminal_fp_per_screen'):
            with self.subTest(key=key):
                bad = dict(ft)
                bad[key] += 0.001 if key == 'terminal_fp_per_screen' else -0.001
                self.assertFalse(all(gate.check_select(self.base, bad).values()))
        base = dict(self.base, terminal_fp_per_screen=4.0)
        self.assertFalse(gate.check_select(base, ft)['terminal FP/screen <= 20% of base'])

    def test_optional_native_and_pooled_ignored(self):
        base = gate.select_metrics(self.base, ['web/val'])
        ft = gate.select_metrics(dict(metrics(), native_precision=0, native_recall=0), ['web/val'])
        checks = gate.check_select(base, ft)
        self.assertEqual(len(checks), 4)
        self.assertTrue(all(checks.values()))
        self.assertFalse(all(gate.check(dict(self.base, web_precision=0.9), ft).values()))

    def run_select(self, documents, mode="select", extra=()):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for i, doc in enumerate(documents):
                path = Path(directory) / f'{i}.json'
                path.write_text(json.dumps(doc))
                paths.append(str(path))
            out, err = io.StringIO(), io.StringIO()
            with patch.object(gate, 'RESULTS', Path(directory)), patch('sys.argv', ['gate', mode, *paths, *extra]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = gate.main()
                except SystemExit as error:
                    code = error.code
            if mode == 'select' and code == 0:
                frozen = json.loads((Path(directory) / 'frozen-ft.json').read_text())
                self.assertEqual(frozen, json.loads(out.getvalue().splitlines()[-1]))
                self.assertEqual(frozen['select_files'], {
                    path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths})
            return code, out.getvalue(), err.getvalue()

    def document(self, iou, thresholds):
        return dict(name='ft', set='select', iou=iou, gui_sets=['web/val', 'native/val'], thresholds=thresholds)

    def test_matched_threshold_and_all_rows_ranked(self):
        base = self.document(0.7, {
            '0.200': dict(self.base, web_only_precision=0.8, web_only_recall=0.5),
            '0.050': self.base,
            '0.100': dict(self.base, web_only_precision=0.8, web_only_recall=0.6)})
        code, out, err = self.run_select([base, self.document(0.4, {
            '0.010': metrics(),
            '0.100': dict(metrics(), web_only_precision=0.75, web_only_recall=0.7)})])
        self.assertEqual((code, err), (0, ''))
        frozen = json.loads(out.splitlines()[-1])
        self.assertEqual({k: frozen[k] for k in ('conf', 'iou', 'base_conf')},
                         dict(conf=0.1, iou=0.4, base_conf=0.1))
        self.assertEqual(frozen['name'], 'ft')
        self.assertEqual(len(frozen['select_files']), 2)
        self.assertIn('base(0.100)', out)

    def test_ranking_tiebreakers(self):
        for key in ('web_only_recall', 'web_only_precision', 'native_recall'):
            with self.subTest(key=key):
                better = dict(metrics())
                better[key] += 0.01
                base = dict(self.base, web_only_precision=0.9)
                code, out, err = self.run_select([
                    self.document(0.7, {'0.050': base}),
                    self.document(0.7, {'0.010': metrics()}),
                    self.document(0.4, {'0.100': better})])
                self.assertEqual((code, err), (0, ''))
                self.assertEqual(json.loads(out.splitlines()[-1])['iou'], 0.4)

    def test_existing_test_sweep_refuses_before_loading_data(self):
        from types import SimpleNamespace
        from train import sweep
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / 'train/results'
            results.mkdir(parents=True)
            destination = results / 'sweep-ft-test-iou0.4.json'
            destination.write_text('preserved')
            args = SimpleNamespace(name='ft', set='test', iou=0.4, force=False)
            with patch.object(sweep, 'R', root), patch('argparse.ArgumentParser.parse_args', return_value=args):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    sweep.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(destination.read_text(), 'preserved')

    def test_ft_names_must_match_and_be_safe(self):
        for name in ('other', '../escape', ''):
            docs = [self.document(0.7, {'0.050': self.base}),
                    self.document(0.4, {'0.010': metrics()}),
                    dict(self.document(0.5, {'0.010': metrics()}), name=name)]
            code, _, _ = self.run_select(docs)
            self.assertEqual(code, 2)

    def test_unreachable_precision(self):
        code, out, _ = self.run_select([
            self.document(0.7, {'0.050': self.base}),
            self.document(0.4, {'0.010': dict(metrics(), web_only_precision=0.9)})])
        self.assertEqual(code, 1)
        self.assertIn('base cannot reach this precision', out)

    def test_gui_sets_required_and_identical(self):
        for target in (0, 1):
            for sources in (None, ['web/val']):
                docs = [self.document(0.7, {'0.050': self.base}),
                        self.document(0.4, {'0.010': metrics()})]
                if sources is None:
                    del docs[target]['gui_sets']
                else:
                    docs[target]['gui_sets'] = sources
                code, _, err = self.run_select(docs)
                self.assertEqual(code, 2)
                self.assertIn('gui_sets', err)

    def test_web_only_omits_native_checks(self):
        docs = [self.document(0.7, {'0.050': self.base}),
                self.document(0.4, {'0.010': dict(metrics(), native_precision=0)})]
        for doc in docs:
            doc['gui_sets'] = ['web/val']
        code, out, _ = self.run_select(docs)
        self.assertEqual(code, 0)
        self.assertNotIn('PASS native', out)

    def test_no_candidate_diagnostics(self):
        code, out, _ = self.run_select([
            self.document(0.7, {'0.050': self.base}),
            self.document(0.4, {'0.010': dict(metrics(), terminal_recall=0.7)})])
        self.assertEqual(code, 1)
        self.assertIn('IoU=0.4 conf=0.010: failed checks: terminal link recall', out)
        self.assertEqual(out.splitlines()[-1], 'OVERALL FAIL: no validation pair passes')

    def test_final_frozen_base_and_missing_threshold(self):
        docs = [dict(set='test', iou=0.7, thresholds={
            '0.050': dict(self.base, web_precision=0.9), '0.100': self.base}),
            dict(name='ft', set='test', iou=0.4, thresholds={'0.020': metrics()})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'frozen.json'
            frozen = dict(name='ft', conf=0.02, iou=0.4, base_conf=0.1)
            path.write_text(json.dumps(frozen))
            code, out, err = self.run_select(docs, 'final', ['--frozen', str(path)])
            self.assertEqual((code, err), (0, ''))
            self.assertIn('OVERALL PASS', out)
            for key, value, message in (('base_conf', 0.3, 'missing threshold 0.300'),
                                        ('conf', 0.3, 'missing threshold 0.300'),
                                        ('name', 'other', 'must match frozen'),
                                        ('iou', 0.7, 'must match frozen')):
                path.write_text(json.dumps(dict(frozen, **{key: value})))
                code, _, err = self.run_select(docs, 'final', ['--frozen', str(path)])
                self.assertEqual(code, 2)
                self.assertIn(message, err)
        code, _, err = self.run_select(docs, 'final')
        self.assertEqual(code, 2)
        self.assertIn('--frozen', err)


if __name__ == '__main__':
    unittest.main()
