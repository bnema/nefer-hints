"""Display-free geometry regression tests."""
import unittest
try:
    from .gtk_app import centre_under, clip_box, intersect, visible_fraction
except ImportError:
    from gtk_app import centre_under, clip_box, intersect, visible_fraction


class GeometryTests(unittest.TestCase):
    def test_intersection(self):
        self.assertEqual(intersect((0, 0, 20, 20), (4, 5, 30, 15)), (4, 5, 20, 15))

    def test_viewport_clipping(self):
        self.assertEqual(clip_box((-5, 0, 15, 10), [(0, 0, 20, 20)]), [0, 0, 15, 10])
        self.assertIsNone(clip_box((-11, 0, 9, 10), [(0, 0, 20, 20)]))
        self.assertEqual(clip_box((-10, 0, 10, 10), [(0, 0, 20, 20)]), [0, 0, 10, 10])

    def test_minimum_size(self):
        self.assertIsNone(clip_box((0, 0, 3, 10), [(0, 0, 20, 20)]))
        self.assertIsNone(clip_box((.2, 0, 3.9, 10), [(0, 0, 20, 20)]))
        self.assertEqual(clip_box((0, 0, 4, 4), [(0, 0, 20, 20)]), [0, 0, 4, 4])
        self.assertIsNone(clip_box((30, 0, 40, 10), [(0, 0, 20, 20)]))

    def test_popup_centre(self):
        self.assertTrue(centre_under((0, 0, 20, 20), (10, 10, 30, 30)))
        self.assertFalse(centre_under((0, 0, 20, 20), (0, 0, 10, 10)))
        self.assertFalse(centre_under((0, 0, 100, 20), (0, 0, 20, 20)))

    def test_visibility_fraction(self):
        self.assertEqual(visible_fraction((0, 0, 10, 10), (0, 0, 5, 10)), .5)
        self.assertEqual(visible_fraction((0, 0, 0, 0), (0, 0, 0, 0)), 0)
        self.assertEqual(visible_fraction((0, 0, 10, 10), (20, 20, 10, 10)), 0)


if __name__ == '__main__':
    unittest.main()
