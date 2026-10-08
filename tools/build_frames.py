"""Rebuild the hero head-turn frames from a folder of illustrated portraits.

Takes every image in SOURCE (sorted by name, so name them left -> right, e.g. 01-..., 02-...),
removes the background, crops them all with ONE shared box so they stay aligned, and writes:

    assets/turn/000.webp, 001.webp, ...   the frames, in order
    assets/turn/front.webp                copy of the straight-on frame (shown before JS loads)
    assets/turn/frames.json               {"count": N, "front": i}, read by index.html

The front frame is the file whose name contains "center" or "front"; otherwise the middle one.

Usage (from the repo root):
    python tools/build_frames.py "C:\\path\\to\\outputs"
    python tools/build_frames.py "C:\\path\\to\\outputs" --front 7 --width 760

Needs Pillow and rembg:  pip install "rembg[cpu]" pillow
"""
import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "turn"


def natural_key(path: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="folder with the ordered head-turn images")
    ap.add_argument("--front", type=int, help="index of the straight-on frame (default: auto)")
    ap.add_argument("--width", type=int, default=760, help="output width in px (default 760)")
    ap.add_argument("--quality", type=int, default=86, help="WebP quality (default 86)")
    args = ap.parse_args()

    files = sorted((f for f in args.source.iterdir() if f.suffix.lower() in IMAGE_EXTS), key=natural_key)
    if len(files) < 2:
        print(f"Need at least 2 images in {args.source}, found {len(files)}.", file=sys.stderr)
        return 1

    sizes = {Image.open(f).size for f in files}
    if len(sizes) > 1:
        print(f"All frames must be the same size; found {sorted(sizes)}.", file=sys.stderr)
        return 1

    try:
        from rembg import new_session, remove
    except ImportError:
        print('rembg is not installed. Run: pip install "rembg[cpu]"', file=sys.stderr)
        return 1

    print(f"Cutting out {len(files)} frames (first run downloads a ~180 MB model)...")
    session = new_session("isnet-general-use")
    cuts = []
    for f in files:
        cuts.append(remove(Image.open(f).convert("RGB"), session=session, post_process_mask=True))
        print("  ", f.name)

    # One shared crop box (union of every subject) keeps the shoulders locked in place.
    boxes = [c.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox() for c in cuts]
    boxes = [b for b in boxes if b]
    pad = 8
    W, H = cuts[0].size
    box = (max(min(b[0] for b in boxes) - pad, 0), max(min(b[1] for b in boxes) - pad, 0),
           min(max(b[2] for b in boxes) + pad, W), min(max(b[3] for b in boxes) + pad, H))

    if args.front is not None:
        front = args.front
    else:
        named = [i for i, f in enumerate(files) if re.search(r"center|centre|front", f.stem, re.I)]
        front = named[0] if named else len(files) // 2
    if not 0 <= front < len(files):
        print(f"--front must be between 0 and {len(files) - 1}.", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("[0-9][0-9][0-9].webp"):
        old.unlink()

    for i, c in enumerate(cuts):
        c = c.crop(box)
        c = c.resize((args.width, round(c.height * args.width / c.width)), Image.LANCZOS)
        c.save(OUT_DIR / f"{i:03d}.webp", "WEBP", quality=args.quality, method=6)
        if i == front:
            c.save(OUT_DIR / "front.webp", "WEBP", quality=args.quality, method=6)

    (OUT_DIR / "frames.json").write_text(json.dumps({"count": len(cuts), "front": front}, indent=2) + "\n")
    print(f"Wrote {len(cuts)} frames to {OUT_DIR} (front = {front}: {files[front].name}).")
    print("If index.html's <img id=\"portrait\"> width/height differ from the new frame size, update them to match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
