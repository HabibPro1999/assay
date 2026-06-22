#!/usr/bin/env python3
"""Convert a generated image that has a FLAT chroma-key background into a clean transparent RGBA PNG.

gpt-image-2 cannot emit a true transparent background, so the RGBA flow is: generate the subject on a
single flat solid key color (default #00ff00), then key that color out here to recover an alpha channel.

Usage
-----
  to_rgba.py --in raw.png --out clean.png --key 00ff00
  to_rgba.py --in raw.png --out clean.png            # auto-detect key from the border
  to_rgba.py --in raw.png --out clean.png --key ff00ff --low 70 --high 165

Tuning
------
  --low   color distance at/below which a pixel is FULLY transparent (default 70)
  --high  color distance at/above which a pixel is FULLY opaque      (default 165)
          (distance is Euclidean RGB, range 0..441). Widen the low..high band for softer,
          more feathered edges; narrow it for crisper cutouts.
  --no-despill   keep the key-color fringe (despill is on by default)
"""
import argparse, sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("to_rgba.py needs Pillow and numpy. Install with: pip install pillow numpy")


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) != 6:
        sys.exit(f"--key must be a 6-digit hex color, got {h!r}")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def auto_key(arr):
    h, w, _ = arr.shape
    b = max(2, min(h, w) // 40)
    frame = np.concatenate([
        arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
        arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3),
    ])
    return np.median(frame, axis=0).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", help="hex key color to remove; auto-detected from border if omitted")
    ap.add_argument("--low", type=float, default=70.0)
    ap.add_argument("--high", type=float, default=165.0)
    ap.add_argument("--no-despill", action="store_true")
    a = ap.parse_args()

    if a.high <= a.low:
        sys.exit("--high must be greater than --low")

    img = Image.open(a.inp).convert("RGB")
    arr = np.asarray(img).astype(np.float32)
    key = hex_to_rgb(a.key) if a.key else auto_key(arr)

    dist = np.sqrt(((arr - key) ** 2).sum(axis=2))
    alpha = np.clip((dist - a.low) / (a.high - a.low), 0.0, 1.0)

    rgb = arr.copy()
    if not a.no_despill:
        # Suppress key-color spill: cap the dominant key channel at the max of the other two.
        kmax = int(np.argmax(key))
        others = [i for i in range(3) if i != kmax]
        cap = arr[:, :, others].max(axis=2)
        rgb[:, :, kmax] = np.minimum(arr[:, :, kmax], cap)

    out = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(a.out)
    opaque = float((alpha > 0.95).mean()) * 100.0
    print(f"{a.out}  (key={'#%02x%02x%02x' % tuple(int(x) for x in key)}, ~{opaque:.0f}% opaque)")


if __name__ == "__main__":
    main()
