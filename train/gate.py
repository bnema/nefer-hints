#!/usr/bin/env python3
"""Select conf/IoU with per-source GUI guards and web-only ranking.

Gate the frozen pair once on TEST using the unchanged pooled GUI checks.
"""
import argparse
import json
from pathlib import Path


def check(base, ft):
    return {
        'web precision drop <= 2 pts': base['web_precision'] - ft['web_precision'] <= 0.02 + 1e-12,
        'web recall drop <= 2 pts': base['web_recall'] - ft['web_recall'] <= 0.02 + 1e-12,
        'terminal FP/screen <= 1.0': ft['terminal_fp_per_screen'] <= 1.0,
        'terminal FP/screen <= 20% of base': ft['terminal_fp_per_screen'] <= 0.2 * base['terminal_fp_per_screen'],
        'terminal link recall >= 80%': ft['terminal_recall'] >= 0.80,
    }


def check_select(base, ft):
    checks = {
        'web-only precision drop <= 2 pts': base['web_only_precision'] - ft['web_only_precision'] <= 0.02 + 1e-12,
        'web-only recall drop <= 2 pts': base['web_only_recall'] - ft['web_only_recall'] <= 0.02 + 1e-12,
    }
    if 'native_precision' in base:
        for metric in ('precision', 'recall'):
            checks[f'native {metric} drop <= 2 pts'] = base[f'native_{metric}'] - ft[f'native_{metric}'] <= 0.02 + 1e-12
    checks.update({
        'terminal FP/screen <= 1.0': ft['terminal_fp_per_screen'] <= 1.0,
        'terminal FP/screen <= 20% of base': ft['terminal_fp_per_screen'] <= 0.2 * base['terminal_fp_per_screen'],
        'terminal link recall >= 80%': ft['terminal_recall'] >= 0.80,
    })
    return checks


def select_metrics(metrics, gui_sets):
    # Older web-only sweeps can contain zero-valued native metrics.
    if 'native/val' not in gui_sets:
        return {key: value for key, value in metrics.items() if not key.startswith('native_')}
    for key in ('native_precision', 'native_recall'):
        if key not in metrics:
            raise ValueError(f'native/val requires {key}')
    return metrics


def read(path, expected_set, base=False):
    data = json.loads(Path(path).read_text())
    if data['set'] != expected_set:
        raise ValueError(f'{path}: expected {expected_set} set')
    if base and data['iou'] != 0.7:
        raise ValueError(f'{path}: base reference must have IoU 0.7')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    select = modes.add_parser('select')
    select.add_argument('base')
    select.add_argument('ft', nargs='+')
    final = modes.add_parser('final')
    final.add_argument('base')
    final.add_argument('ft')
    final.add_argument('--conf', type=float, required=True)
    args = parser.parse_args()
    try:
        expected = 'select' if args.mode == 'select' else 'test'
        base_data = read(args.base, expected, base=True)
        base = base_data['thresholds']['0.050']
        if args.mode == 'select':
            if 'gui_sets' not in base_data:
                raise ValueError(f'{args.base}: select file requires gui_sets')
            gui_sets = base_data['gui_sets']
            base = select_metrics(base, gui_sets)
            candidates = []
            diagnostics = []
            seen = set()
            for path in args.ft:
                data = read(path, expected)
                if 'gui_sets' not in data or data['gui_sets'] != gui_sets:
                    raise ValueError(f'{path}: gui_sets must match base {gui_sets!r}')
                if data['iou'] in seen:
                    raise ValueError('provide only one fine-tuned file per IoU')
                seen.add(data['iou'])
                thresholds = sorted(data['thresholds'], key=float)
                for threshold in thresholds:
                    metrics = select_metrics(data['thresholds'][threshold], gui_sets)
                    checks = check_select(base, metrics)
                    if threshold == thresholds[0]:
                        diagnostics.append((data['iou'], threshold, checks))
                    if all(checks.values()):
                        candidates.append((metrics, float(threshold), data['iou']))
                        break
            if not candidates:
                for iou, threshold, checks in diagnostics:
                    print(f'IoU={iou:g} conf={threshold}: failed checks: ' +
                          ', '.join(label for label, passed in checks.items() if not passed))
                print('OVERALL FAIL: no validation pair passes')
                return 1
            ft, conf, iou = max(candidates, key=lambda c: (
                c[0]['web_only_precision'], c[0]['web_only_recall'], c[0].get('native_precision', 0)))
            print(f'Selected conf={conf:g}, IoU={iou:g}')
            for name, metrics in (('base', base), ('ft', ft)):
                print(name, json.dumps(metrics, sort_keys=True))
            for label, passed in check_select(base, ft).items():
                print('PASS' if passed else 'FAIL', label)
            print(json.dumps(dict(conf=conf, iou=iou)))
            return 0
        data = read(args.ft, expected)
        ft = data['thresholds'][f'{args.conf:.3f}']
        print(f"Frozen conf={args.conf:g}, IoU={data['iou']:g}")
        for name, metrics in (('base', base), ('ft', ft)):
            print(name, json.dumps(metrics, sort_keys=True))
            print(f"{name} independent web P={metrics['web_precision_independent']:.6f} R={metrics['web_recall_independent']:.6f} (informational)")
        checks = check(base, ft)
        for label, passed in checks.items():
            print('PASS' if passed else 'FAIL', label)
        passed = all(checks.values())
        print('OVERALL', 'PASS' if passed else 'FAIL')
        return 0 if passed else 1
    except (ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
