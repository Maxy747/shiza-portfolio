# Shizanourin T.A. — portfolio

Single-page portfolio for Shiza: project management, cybersecurity and content creation.
Plain HTML/CSS/JS in `index.html`, no build step. Smooth scrolling uses [Lenis](https://github.com/darkroomengineering/lenis) from jsDelivr.

Live: https://maxy747.github.io/shiza-portfolio/

## Run locally

```bash
python -m http.server 5173
```

Then open http://localhost:5173. Opening `index.html` straight from disk mostly works, but the head-turn frame list is fetched, so use a server.

## Updating the head-turn frames

The hero portrait scrubs through `assets/turn/000.webp … NNN.webp` as the cursor moves. To swap in a new set:

```bash
pip install "rembg[cpu]" pillow
python tools/build_frames.py "C:\Users\MoeLustHer\Documents\Codex\2026-10-08\a-stylized-illustrated-portrait-in-maheen\outputs"
git add assets/turn && git commit -m "Update head-turn frames" && git push
```

Name the source images so they sort left → right (`01-…`, `02-…`). The straight-on frame is the one named `center`/`front`, or pass `--front N`. All frames must be the same size. More frames = smoother turn; 15–30 looks close to continuous.

## Credits

Site by [Max](https://github.com/Maxy747). Layout and motion inspired by Maheen Dossal's portfolio, used with permission.
