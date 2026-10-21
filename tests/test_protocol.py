"""Run with venv/bin/python -m unittest discover -s tests -v."""
import struct
import unittest
import cv2
import numpy as np
from protocol import Client, ROOT

class ProtocolTests(unittest.TestCase):
    def test_eof(self):
        c=Client(640)
        self.assertEqual(c.close(),0)
    def test_bad_magic(self):
        c=Client(640);c.send(b'NOPE')
        self.assertEqual(c.close(),2)
    def test_truncated_magic(self):
        c=Client(640);c.send(b'NH')
        self.assertEqual(c.close(),2)
    def test_truncated_payload(self):
        c=Client(640)
        c.send(struct.pack('<4sIQIIIIIf',b'NHRQ',1,42,32,32,128,1,0,0))
        c.p.stdin.close()
        r=c.response();self.assertEqual((r['seq'],r['status']),(42,1))
        self.assertEqual(c.p.wait(timeout=60),2);c.p.stdout.close();c.log.close()
    def test_bad_version(self):
        c=Client(640);c.send(struct.pack('<4sIQ',b'NHRQ',2,43))
        self.assertEqual(c.response()['seq'],43)
        self.assertEqual(c.close(),2)
    def test_huge_dimensions_and_stride(self):
        for w,h,stride in [(1<<29,2,0xffffffff),(100,100,399),(1,2,0xffffffff)]:
            with self.subTest(w=w,h=h,stride=stride):
                c=Client(640);c.send(struct.pack('<4sIQIIIII',b'NHRQ',1,44,w,h,stride,1,0))
                self.assertEqual(c.response()['status'],1)
                self.assertEqual(c.close(),2)
    def test_recovery_and_regions(self):
        c=Client(640)
        image=cv2.cvtColor(cv2.imread(str(ROOT/'poc/2026-10-21-omniparser/frames/firefox-menu.png')),cv2.COLOR_BGR2BGRA)
        for kwargs in [dict(format=2),dict(regions=[(9999,0,1,1)]),dict(regions=[(0,0,1,1)]*65),dict(conf=float('nan'))]:
            self.assertEqual(c.request(image,**kwargs)['status'],1)
        whole=c.request(image,seq=1<<40)
        self.assertEqual(whole['status'],0);self.assertEqual(whole['seq'],1<<40)
        self.assertGreater(len(whole['boxes']),0)
        multi=c.request(image,regions=[(-10,-10,970,1090),(960,0,960,1080)])
        self.assertEqual(multi['status'],0)
        self.assertEqual({b[5] for b in multi['boxes']},{0,1})
        for b in multi['boxes']:
            self.assertTrue(0<=b[0]<=b[2]<=1920)
            self.assertTrue(0<=b[1]<=b[3]<=1080)
            self.assertTrue((b[2]<=960) if b[5]==0 else (b[0]>=960))
        self.assertEqual(c.close(),0)
    def test_cpu(self):
        c=Client(640,('--gpu','cpu'))
        self.assertEqual(c.device,'CPU')
        self.assertEqual(c.request(np.zeros((32,32,4),np.uint8))['status'],0)
        self.assertEqual(c.close(),0)
if __name__=='__main__': unittest.main()
