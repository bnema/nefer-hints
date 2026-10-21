#!/usr/bin/env python3
"""usage: gate.py <base-summary.json> <ft-summary.json>; exit 0 on PASS. Criteria at conf 0.05."""
import json, sys
b, f = (json.load(open(p))['0.05'] for p in sys.argv[1:3])
c = {
 'eval TEST recall drop <= 2 pts': (b['eval_test_recall'] - f['eval_test_recall']) * 100 <= 2,
 'eval TEST precision drop <= 2 pts': (b['eval_test_precision'] - f['eval_test_precision']) * 100 <= 2,
 'terminal FP/screen <= 1.0': f['terminal_fp_per_screen'] <= 1.0,
 'terminal FP/screen >= 80% lower than base': f['terminal_fp_per_screen'] <= 0.2 * b['terminal_fp_per_screen'],
 'terminal link recall >= 80%': f['terminal_recall'] >= 0.80,
}
for k, v in c.items(): print('PASS' if v else 'FAIL', k)
ok = all(c.values()); print('OVERALL', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
