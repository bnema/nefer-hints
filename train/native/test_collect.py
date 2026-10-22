import unittest
from train.native.collect import split_for, variant, plan, yolo_boxes, merge_manifest


class Helpers(unittest.TestCase):
    def test_split_and_counts(self):
        rows = plan()
        self.assertEqual(len(rows), 620)
        for toolkit in ('gtk', 'qt'):
            self.assertEqual(sum(r['toolkit'] == toolkit and r['split'] == 'train' for r in rows), 260)
            self.assertEqual(sum(r['toolkit'] == toolkit and r['split'] == 'val' for r in rows), 50)
        self.assertEqual(split_for('table'), 'val')
        self.assertEqual(split_for('preferences-dialog'), 'val')
        self.assertEqual(split_for('form'), 'train')
        with self.assertRaises(ValueError):
            split_for('unknown')

    def test_id(self):
        self.assertEqual(variant('gtk', 'form', 1), variant('gtk', 'form', 1))
        self.assertNotEqual(variant('gtk', 'form', 1)['id'], variant('qt', 'form', 1)['id'])
        self.assertEqual(len({r['id'] for r in plan()}), 620)

    def test_yolo(self):
        self.assertEqual(yolo_boxes([[-10, -20, 50, 100, 'field'], [1, 1, 3, 9, 'field'], [20, 20, 10, 10, 'field']], 100, 100),
                         [(0.25, 0.5, 0.5, 1.0)])
        with self.assertRaises(ValueError):
            yolo_boxes([[0, 0, float('nan'), 10]], 100, 100)

    def test_merge(self):
        self.assertEqual(merge_manifest([{'id': 'a', 'n_boxes': 3}, {'id': 'b'}],
                                       [{'id': 'a', 'n_boxes': 4}]),
                         [{'id': 'a', 'n_boxes': 4}, {'id': 'b'}])


if __name__ == '__main__':
    unittest.main()
