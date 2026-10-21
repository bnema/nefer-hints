"""AGPL-3.0-only. Offline exports; direct pnnx workaround for missing ncnn Python binding."""
import os
os.environ.update(YOLO_OFFLINE='true',HF_HUB_OFFLINE='1',YOLO_AUTOINSTALL='false')
from pathlib import Path
import subprocess
import json
import onnx
import onnxslim
from ultralytics import YOLO
ROOT=Path(__file__).resolve().parents[3]
os.chdir(ROOT)
logs=[]
for size in [640,1280]:
    for simplify in [False,True]:
        try:
            path=YOLO('weights/model.pt').export(format='onnx',imgsz=size,opset=17,dynamic=False,simplify=simplify)
            Path(path).rename(f'weights/model-{size}{"-slim" if simplify else ""}.onnx')
            logs.append(dict(format='onnx',imgsz=size,simplify=simplify,status='ok'))
        except Exception as e:logs.append(dict(format='onnx',imgsz=size,simplify=simplify,error=repr(e)))
    try:
        path=YOLO('weights/model.pt').export(format='ncnn',imgsz=size,dynamic=False)
        Path(path).rename(f'weights/model-{size}_ncnn_model')
    except Exception as e:
        logs.append(dict(format='ncnn',imgsz=size,error=repr(e),workaround='ultralytics torchscript export + installed pnnx CLI, no Python ncnn binding needed'))
        path=YOLO('weights/model.pt').export(format='torchscript',imgsz=size)
        folder=ROOT/f'weights/model-{size}_ncnn_model';folder.mkdir(exist_ok=True)
        r=subprocess.run([str(ROOT/'venv/bin/pnnx'),str(ROOT/path),f'inputshape=[1,3,{size},{size}]','fp16=0'],cwd=folder,capture_output=True,text=True,timeout=120)
        (folder/'export.log').write_text(r.stdout+r.stderr)
        # pnnx names outputs after the absolute input path; move those to the target directory.
        for suffix in ['ncnn.param','ncnn.bin']:
            src=ROOT/f'weights/model.{suffix}'
            if src.exists():src.rename(folder/f'model.{suffix}')
        logs.append(dict(format='pnnx',imgsz=size,returncode=r.returncode,log=r.stdout+r.stderr))
(Path(__file__).resolve().parents[1]/'export.json').write_text(json.dumps(logs,indent=2))
