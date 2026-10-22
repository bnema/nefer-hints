#!/usr/bin/env python3
"""Fine-tune the OmniParser icon_detect base on terminal (links only) + web data.

  venv/bin/python train/finetune.py [--batch 2] [--epochs 40] [--device 0] [--vram-gib 10]

Use train/run_train.sh to run it as a low-priority, memory-capped systemd unit.
--vram-gib caps this process's GPU memory so the compositor keeps room for its
framebuffers; without it, training fills the whole GPU and the session freezes.
"""
import os
os.environ.update(YOLO_OFFLINE='true', HF_HUB_OFFLINE='1', YOLO_AUTOINSTALL='false')
import argparse, time
from pathlib import Path
from ultralytics import YOLO
R = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int, default=2); ap.add_argument('--epochs', type=int, default=40)
    ap.add_argument('--device', default='0'); ap.add_argument('--workers', type=int, default=2); ap.add_argument('--name', default='ft')
    ap.add_argument('--vram-gib', type=float, default=10, help='GPU memory cap for this process (0 = no cap)')
    ap.add_argument('--fraction', type=float, default=1.0, help='dataset fraction (smoke tests)')
    a = ap.parse_args()
    if a.vram_gib > 0 and a.device.isdigit():
        import torch
        total = torch.cuda.get_device_properties(int(a.device)).total_memory
        torch.cuda.set_per_process_memory_fraction(min(1.0, a.vram_gib * 2**30 / total), int(a.device))
    yaml = R / 'data/ft.yaml'
    D = R / 'data'
    yaml.write_text('path: %s\ntrain:\n  - terminal/train/images\n  - web/train/images\nval:\n  - terminal/val/images\n  - web/val/images\nnc: 1\nnames:\n  0: clickable\n' % D)
    t = time.time()
    m = YOLO(str(R / 'weights/base.pt'))
    m.train(data=str(yaml), imgsz=1280, rect=False, epochs=a.epochs, patience=10, batch=a.batch, lr0=0.002, lrf=0.1, optimizer='AdamW',
            warmup_epochs=1, mosaic=0.0, mixup=0.0, fliplr=0.0, flipud=0.0, hsv_h=0.0, hsv_s=0.0, hsv_v=0.2, scale=0.25, translate=0.05,
            degrees=0, amp=False, device=int(a.device) if a.device.isdigit() else a.device, workers=a.workers, project=str(R / 'runs'), name=a.name, seed=0, exist_ok=True, fraction=a.fraction)
    print('WALL_SECONDS', round(time.time() - t))


if __name__ == '__main__':
    main()
