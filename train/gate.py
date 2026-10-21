#!/usr/bin/env python3
"""Install gate. The base model is always judged at conf 0.05.

  gate.py <base-summary.json> <ft-summary.json>      fine-tuned model at conf 0.05
  gate.py --sweep <sweep-base.json> <sweep-ft.json>   lowest fine-tuned conf that passes

Exit 0 on PASS. With --sweep, prints the chosen conf (ship it as hint.threshold).
"""
import json, sys


def check(b, f):
    return {
        'eval TEST recall drop <= 2 pts': (b['eval_test_recall'] - f['eval_test_recall']) * 100 <= 2,
        'eval TEST precision drop <= 2 pts': (b['eval_test_precision'] - f['eval_test_precision']) * 100 <= 2,
        'terminal FP/screen <= 1.0': f['terminal_fp_per_screen'] <= 1.0,
        'terminal FP/screen >= 80% lower than base': f['terminal_fp_per_screen'] <= 0.2 * b['terminal_fp_per_screen'],
        'terminal link recall >= 80%': f['terminal_recall'] >= 0.80,
    }


def main(argv):
    if argv[:1] == ['--sweep']:
        bs, fs = (json.load(open(p))['thresholds'] for p in argv[1:3])
        b = bs['0.050']
        for t in sorted(fs, key=float):
            c = check(b, fs[t])
            if all(c.values()):
                print('PASS at conf', t, json.dumps(fs[t]))
                return 0
        best = max(fs, key=lambda t: sum(check(b, fs[t]).values()))
        for k, v in check(b, fs[best]).items(): print('PASS' if v else 'FAIL', k)
        print('OVERALL FAIL (closest conf %s)' % best, json.dumps(fs[best]))
        return 1
    b, f = (json.load(open(p))['0.05'] for p in argv[:2])
    c = check(b, f)
    for k, v in c.items(): print('PASS' if v else 'FAIL', k)
    ok = all(c.values()); print('OVERALL', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
