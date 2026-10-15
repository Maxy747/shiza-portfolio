"""Build hero frames where only the background around her head is transparent.

The clothes and everything from the shoulders down keep the original photo (background included);
above that, the background around her hair is cut away so the name behind her shows through.
A soft vertical blend between the two avoids a visible line.

Usage (from the repo root):
    python tools/build_hair_cutout.py "C:\\path\\to\\outputs\\striped-frame-manifest.json" --out assets/striped-hair

The manifest is Codex's {"centerIndex": n, "frames": [{"file": ..., "position": ...}, ...]}.
Needs Pillow and rembg:  pip install "rembg[cpu]" pillow
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path, help="Codex frame manifest (JSON)")
    ap.add_argument("--out", type=Path, required=True, help="output folder, e.g. assets/striped-hair")
    ap.add_argument("--top-trim", type=int, default=80, help="px of empty background to trim above the hair (default 80)")
    ap.add_argument("--blend-start", type=float, default=.50, help="fraction of height where the photo starts fading back in (default .50)")
    ap.add_argument("--blend-end", type=float, default=.62, help="fraction of height where the photo is fully opaque again (default .62)")
    ap.add_argument("--width", type=int, default=760)
    ap.add_argument("--quality", type=int, default=86)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    frames = manifest["frames"]
    files = [args.manifest.parent / f["file"] for f in frames]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        print(f"Manifest lists files that don't exist: {missing}", file=sys.stderr)
        return 1

    try:
        from rembg import new_session, remove
    except ImportError:
        print('rembg is not installed. Run: pip install "rembg[cpu]"', file=sys.stderr)
        return 1
    session = new_session("u2net_human_seg")  # people model: keeps hair and clothes, ignores colour look-alikes

    sizes = {Image.open(f).size for f in files}
    W, H = min(w for w, _ in sizes), min(h for _, h in sizes)
    y0, y1 = int(H * args.blend_start), int(H * args.blend_end)
    ramp = Image.linear_gradient("L").resize((W, max(y1 - y0, 1)))  # 0 at top → 255 at bottom
    keep_below = Image.new("L", (W, H), 0)
    keep_below.paste(ramp, (0, y0))
    keep_below.paste(255, (0, y1, W, H))

    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("[0-9][0-9][0-9].webp"):
        old.unlink()
    front = int(manifest.get("centerIndex", len(files) // 2))
    for i, f in enumerate(files):
        img = Image.open(f).convert("RGB").crop((0, 0, W, H))
        person = remove(img, session=session, only_mask=True, post_process_mask=True)
        alpha = ImageChops.lighter(person, keep_below)  # her outline up top, the full photo below
        out = img.convert("RGBA")
        out.putalpha(alpha)
        out = out.crop((0, args.top_trim, W, H))
        out = out.resize((args.width, round(out.height * args.width / out.width)), Image.LANCZOS)
        out.save(args.out / f"{i:03d}.webp", "WEBP", quality=args.quality, method=6)
        if i == front:
            out.save(args.out / "front.webp", "WEBP", quality=args.quality, method=6)
        print("  ", f.name)

    meta = {"count": len(files), "front": front, "positions": [round(float(f["position"]), 4) for f in frames]}
    (args.out / "frames.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {len(files)} frames to {args.out} (front = {front}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
