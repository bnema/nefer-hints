#!/usr/bin/env python3
"""Select conf/IoU on validation, then gate the frozen pair once on TEST."""
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
        base = read(args.base, expected, base=True)['thresholds']['0.050']
        if args.mode == 'select':
            candidates = []
            seen = set()
            for path in args.ft:
                data = read(path, expected)
                if data['iou'] in seen:
                    raise ValueError('provide only one fine-tuned file per IoU')
                seen.add(data['iou'])
                for threshold in sorted(data['thresholds'], key=float):
                    metrics = data['thresholds'][threshold]
                    if all(check(base, metrics).values()):
                        candidates.append((metrics, float(threshold), data['iou']))
                        break
            if not candidates:
                print('OVERALL FAIL: no validation pair passes')
                return 1
            _, conf, iou = max(candidates, key=lambda c: (c[0]['web_precision'], c[0]['web_recall']))
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
