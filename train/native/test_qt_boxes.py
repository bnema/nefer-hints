"""Pure geometry tests: no Qt import or display required."""
import unittest

try:
    from .qt_app import clip_box, covered
except ImportError:
    from qt_app import clip_box, covered


class BoxTests(unittest.TestCase):
    def test_inside(self):
        self.assertEqual(clip_box((4, 5, 20, 30), (0, 0, 100, 100)), [4, 5, 20, 30])

    def test_exact_half_is_kept(self):
        self.assertEqual(clip_box((-10, 0, 10, 10), (0, 0, 100, 100)), [0, 0, 10, 10])

    def test_mostly_hidden(self):
        self.assertIsNone(clip_box((-11, 0, 9, 10), (0, 0, 100, 100)))

    def test_tiny_and_empty(self):
        for rect in [(0, 0, 3, 100), (0, 0, 100, 3), (0, 0, 0, 10), (20, 20, 10, 10)]:
            with self.subTest(rect=rect):
                self.assertIsNone(clip_box(rect, (0, 0, 100, 100)))

    def test_output_clip(self):
        self.assertEqual(clip_box((90, 90, 110, 110), (0, 0, 100, 100), 0), [90, 90, 100, 100])

    def test_offscreen(self):
        self.assertIsNone(clip_box((110, 0, 130, 10), (0, 0, 100, 100)))

    def test_occlusion_uses_center_not_overlap(self):
        self.assertFalse(covered((0, 0, 100, 20), (0, 0, 30, 20)))
        self.assertTrue(covered((0, 0, 100, 20), (40, 0, 60, 20)))

    def test_exclusive_occlusion_edge(self):
        self.assertFalse(covered((0, 0, 20, 20), (0, 0, 10, 10)))
        self.assertTrue(covered((0, 0, 20, 20), (10, 10, 30, 30)))


if __name__ == '__main__':
    unittest.main()
