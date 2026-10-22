import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import unittest
from score import match, metrics


class MatchingTests(unittest.TestCase):
    def test_augmenting_path_not_greedy(self):
        # First prediction fits both targets; second only fits the wide target.
        pairs = match([[1,1,3,3], [7,1,9,3]], [[0,0,10,10], [0,0,4,4]])
        self.assertEqual(pairs, {1:0, 0:1})

    def test_duplicates_count_in_precision_denominator(self):
        boxes = [[1,1,3,3]]*3
        pairs = match(boxes, [[0,0,4,4]])
        self.assertEqual(len(pairs), 1)
        result = metrics([dict(tp=len(pairs), predictions=3, targets=1, protocol_ms=10)])
        self.assertEqual(result['precision'], 1/3)
        self.assertEqual(result['recall'], 1)

    def test_empty(self):
        self.assertEqual(match([], [[0,0,4,4]]), {})
        self.assertEqual(match([[0,0,4,4]], []), {})
        self.assertIsNone(metrics([])['precision'])
        self.assertIsNone(metrics([])['recall'])

    def test_centre_not_iou(self):
        self.assertEqual(match([[-100,-100,104,104]], [[1,1,3,3]]), {0:0})

    def test_boundary_inclusive(self):
        self.assertEqual(match([[0,0,2,2]], [[1,1,3,3]]), {0:0})

    def test_aggregate_is_micro_not_mean(self):
        result = metrics([dict(tp=1,predictions=1,targets=2,protocol_ms=1),
                          dict(tp=0,predictions=9,targets=8,protocol_ms=3)])
        self.assertEqual(result['precision'], .1)
        self.assertEqual(result['recall'], .1)
        self.assertEqual(result['protocol_median_ms'], 2)


if __name__ == '__main__':
    unittest.main()
