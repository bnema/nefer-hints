"""Focused consistency checks; run after report.py."""
import json
import unittest
from pathlib import Path
from report import agreement
from score import match

class Checks(unittest.TestCase):
    def test_matching(self):
        owners,_=match([(5,5),(15,5)],[[0,0,20,10],[0,0,10,10]])
        self.assertEqual(len(owners),2)
    def test_agreement(self):
        boxes=[[0,0,10,10],[0,0,0,0]]
        self.assertFalse(agreement(boxes,boxes)['flag'])
        self.assertTrue(agreement(boxes,boxes[:1])['flag'])
    def test_measurements(self):
        d=json.loads((Path(__file__).resolve().parents[1]/'results.json').read_text())
        self.assertEqual(len(d['runs']),16)
        for r in d['runs']:
            self.assertEqual(len(r['scenes']),7)
            self.assertEqual(r['score']['gt'],595)
            for s in r['scenes'].values():
                for k in ['inference_ms','e2e_ms']:
                    self.assertEqual(len(s[k]),20)
                    self.assertTrue(all(v>0 for v in s[k]))
            if r['backend'] in ['torch-cpu','torch-gpu-fp32','ort-cpu','ort-gpu','ort-gpu-slim']:
                self.assertTrue(all(not a['flag'] for a in r['agreement'].values()))
        self.assertTrue(all(not a['flag'] for a in d['rect_validation']['agreement_with_original'].values()))
        self.assertAlmostEqual(d['rect_validation']['score']['precision'],.7089201878)
        self.assertAlmostEqual(d['rect_validation']['score']['recall'],.7613445378)
if __name__=='__main__':unittest.main()
