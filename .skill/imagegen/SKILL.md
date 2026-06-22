---
name: imagegen
description: >-
  Generate any raster image with GPT-image-2 through the user's ChatGPT/Codex subscription — no
  OPENAI_API_KEY and no per-image API cost. Use this whenever the user wants to create, generate,
  make, render, or design an image, picture, graphic, asset, infographic, diagram, icon, app icon,
  logo concept, mockup, UI mockup, illustration, hero image, sprite, game asset, texture, banner,
  wallpaper, avatar, or sticker — even if they don't say "image" outright (e.g. "I need a thumbnail
  for this", "make me something to put on the slide", "design a mascot"). ALWAYS use this skill for
  image creation rather than writing your own PIL/SVG/matplotlib code, because that produces a
  drawing, not a real generated image. Triggers on the /imagegen command. If the first argument is
  RGBA (e.g. "/imagegen RGBA a fox mascot"), produce a clean transparent-background RGBA PNG.
---

# imagegen

Generate a real GPT-image-2 image from a natural-language request and save it as a PNG — billed to
the user's ChatGPT/Codex subscription, not a paid API key. Optionally deliver it as a clean
transparent **RGBA** cutout.

## Why this works (the technique)

The Codex CLI ships a built-in `image_gen` tool (gpt-image-2) that runs on the user's subscription.
We drive it headlessly: `codex exec` with a prompt that starts with `$imagegen` and hard rules that
force the *native* tool (not a code/SVG fallback, not the paid API). Under `codex exec` the PNG is
returned inline as base64 inside the session rollout JSONL — it is **not** written to disk by codex —
so we decode it ourselves. `scripts/codex_imagegen.py` does all of this; you just supply a good
prompt and an output path.

This means: do not hand-draw with PIL/SVG, and do not reach for `OPENAI_API_KEY`. The whole point is
free, subscription-backed, genuine gpt-image-2 output.

## Workflow

1. **Parse the request.** Strip a leading `RGBA` token (case-insensitive) if present — that selects
   transparent mode. Everything else is the description of what to make.

2. **Decide output path.** Default to the current working directory with a short descriptive,
   kebab-case filename (e.g. `./coffee-shop-logo.png`). If the user named a folder/path or you're in
   a project with an obvious assets dir, save there. For a multi-image set, number them
   (`01-...png`, `02-...png`).

3. **Craft the prompt.** Expand the user's request into one strong gpt-image-2 instruction. Keep the
   user's intent; add only the detail that materially helps. See `references/prompting.md` for the
   prompt shape, asset-type defaults, in-image text rules, and size guidance. Pass the description
   WITHOUT a `$imagegen` prefix — the script adds it. If the user asked for several images, craft a
   distinct prompt per image and reuse one shared house-style block so the set is cohesive.

4. **Generate.** Run the script (a generation takes ~40–120s):

   ```bash
   python3 ~/.claude/skills/imagegen/scripts/codex_imagegen.py \
     --out <output.png> --prompt "<your crafted prompt>"
   ```

   It prints the saved absolute path. For many images, loop one call per image (they can also run in
   the background in parallel).

5. **RGBA mode (only if requested).** gpt-image-2 can't emit true transparency, so use the
   chroma-key flow: craft the prompt to place the subject on a flat solid key color, generate, then
   key it out.
   - Add to the prompt: "on a perfectly flat solid #00ff00 chroma-key background — one uniform
     color, no gradient, no shadow, no floor, no reflection; crisp clean edges with generous
     padding; do not use #00ff00 anywhere in the subject."
   - Pick a key the subject won't contain: default `#00ff00`; for green subjects use `#ff00ff`.
   - Generate to a temp raw file, then convert:

     ```bash
     python3 ~/.claude/skills/imagegen/scripts/codex_imagegen.py --out <raw>.png --prompt "<prompt with chroma bg>"
     python3 ~/.claude/skills/imagegen/scripts/to_rgba.py --in <raw>.png --out <final>.png --key 00ff00
     ```
   - Inspect the result. If a colored fringe remains, widen the band (`--high 180`) or re-run; if
     edges are too hard, raise `--low`/`--high` together for a softer matte.
   - Chroma-key is poor for wispy edges (hair, fur, smoke, glass). If the subject needs that, tell
     the user honestly that a clean cutout there would need the paid-API true-transparency path,
     which this skill deliberately avoids — offer a solid-background version instead.

6. **Verify and report.** Open the saved PNG to confirm the subject, composition, and any in-image
   text are correct (text especially — re-run with shortened labels if it's garbled). Then report
   the final path(s) and show the image to the user. Iterate with one targeted change at a time.

## Output contract

ALWAYS end by telling the user the exact saved path(s). For RGBA, deliver the transparent PNG as the
primary artifact (you may keep the raw keyed version alongside it, or clean it up — your call based
on whether the user might want to re-key it).

## Notes & troubleshooting

- **Fell back / no image produced:** the script fails loudly if codex didn't call the native tool.
  The hard rules normally prevent this; if it recurs, simplify the prompt and confirm `codex login`
  is active and `codex features list | grep image_generation` is `true`.
- **Cost awareness:** image turns consume the ChatGPT plan's usage faster than text turns. Generate
  deliberately; don't spray variants unless asked.
- **Text-heavy infographics:** keep every label short and list them verbatim in the prompt. If exact,
  dense, pixel-perfect text is the hard requirement, a vector/HTML render may beat a generated image
  — mention that option, but default to genuine generation since that's what this skill is for.
- **Dependencies:** RGBA mode needs Pillow + numpy (`pip install pillow numpy`). Generation itself
  needs only the Codex CLI.

## Files

- `scripts/codex_imagegen.py` — generate via subscription gpt-image-2; decode the rollout to a PNG.
- `scripts/to_rgba.py` — chroma-key a flat background into a clean transparent RGBA PNG.
- `references/prompting.md` — how to craft gpt-image-2 prompts (read before writing the prompt).
