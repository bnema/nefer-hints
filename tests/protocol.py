"""Small synchronous protocol client; timeout enforced on all pipe reads."""
import os
import select
import struct
import subprocess
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class Client:
    def __init__(self, size=1280, extra=()):
        self.log = open(ROOT/'weights/test-stderr.log', 'ab')
        start = time.perf_counter()
        self.p = subprocess.Popen([os.environ.get('NEFER_HINTS_RUNNER', str(ROOT/'build/nefer-hints')), '--model', str(ROOT/'models'), '--imgsz', str(size), *extra], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, bufsize=0)
        assert self.read(4) == b'NHNT'
        version, status = self.unpack('II')
        assert version == 1
        self.device = self.string()
        if status: raise RuntimeError(self.device)
        assert self.unpack('I')[0] == size
        self.cold_ms = (time.perf_counter()-start)*1000
    def read(self, n):
        out = bytearray()
        deadline = time.monotonic()+60
        while len(out)<n:
            if not select.select([self.p.stdout], [], [], max(0, deadline-time.monotonic()))[0]:
                raise TimeoutError('runner read')
            chunk = os.read(self.p.stdout.fileno(), n-len(out))
            if not chunk: raise EOFError('runner closed stdout')
            out.extend(chunk)
        return bytes(out)
    def unpack(self, fmt):
        return struct.unpack('<'+fmt, self.read(struct.calcsize('<'+fmt)))
    def string(self):
        return self.read(self.unpack('I')[0]).decode()
    def send(self, data):
        view = memoryview(data)
        while view:
            n = self.p.stdin.write(view)
            view = view[n:]
    def response(self):
        assert self.read(4)==b'NHRS'
        version, seq, status = self.unpack('IQI')
        assert version==1
        if status: return dict(seq=seq, status=status, error=self.string())
        ms, count = self.unpack('fI')
        boxes = [self.unpack('fffffI') for _ in range(count)]
        return dict(seq=seq,status=0,inference_ms=ms,boxes=boxes)
    def request(self, image, seq=1, regions=(), conf=0, format=1):
        h,w = image.shape[:2]
        data = struct.pack('<4sIQIIIII', b'NHRQ',1,seq,w,h,w*4,format,len(regions))
        data += b''.join(struct.pack('<iiII',*r) for r in regions)+struct.pack('<f',conf)+image.tobytes()
        self.send(data)
        return self.response()
    def close(self):
        self.p.stdin.close()
        code = self.p.wait(timeout=60)
        self.p.stdout.close()
        self.log.close()
        return code
