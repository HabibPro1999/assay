# Crafting GPT-image-2 prompts

Read this when you need to turn a short user request into a strong image prompt. The model is
capable but literal: it renders what you describe and struggles with long paragraphs of dense text.
Your job is to expand a thin request just enough to be unambiguous — not to bolt on creative details
the user did not ask for.

## The shape of a good prompt

Order matters. Lead with scene/backdrop, then subject, then details, then constraints:

```
<art direction / medium / style> — <composition & framing> — <subject and its details> —
<lighting & mood> — <palette> — exact text (verbatim, in quotes) — <constraints / avoid>
```

Keep it one flowing instruction, a few sentences. End with what to avoid (e.g. "no watermark, no
gibberish text").

## Specificity policy

- If the user's request is already detailed, normalize it into a clean spec — don't inflate it.
- If it's generic ("make me a logo for a coffee shop"), add tasteful, expected detail (medium,
  composition, palette, mood) that materially improves the result. Never invent brand names,
  slogans, extra characters, or narrative beats the user didn't imply.

## Pick an asset type and let it set the defaults

| User wants… | Lean toward |
| --- | --- |
| infographic / diagram / explainer | flat editorial vector look, clear zones, big title, SHORT labels, strong reading path |
| icon / app icon / logo concept | simple geometric, centered, minimal, bold silhouette, few colors |
| product mockup | clean studio photography, soft lighting, negative space for copy |
| UI / web / app mockup | crisp screens, realistic layout, state the fidelity (wireframe vs polished) |
| illustration / hero art | named medium (flat, 3D, watercolor, isometric…), depth, mood |
| sprite / game asset | consistent style, orthographic or 3/4 view, plain background |
| photorealistic scene | camera language: lens, angle, depth of field, natural light |

## Text inside images

Short labels render well; paragraphs do not. So:

- Quote the exact text verbatim and keep each label short.
- List the labels explicitly and say "render ONLY this text, spelled correctly; no other text, no
  gibberish letters, no watermark."
- For a tricky/critical word, you can spell it out and demand verbatim rendering.

## Size & orientation

State it in the prompt in plain words ("landscape", "square", "tall portrait"). Good defaults:
- Landscape / slide / banner → 1536x1024
- Square / icon / social → 1024x1024
- Portrait / phone / story → 1024x1536

## Consistency across a set

When generating several related images, repeat the SAME palette, style sentence, and framing rules
in every prompt so the set looks cohesive. A reusable "house style" block pays off — define it once
and prepend it to each prompt.

## Transparent / RGBA subjects (chroma-key flow)

gpt-image-2 cannot produce true transparency, so for cutouts we generate on a flat key color and
remove it afterward (see SKILL.md "RGBA mode"). When building an RGBA prompt:

- Put the subject on "a perfectly flat solid #00ff00 chroma-key background, one uniform color, no
  gradient, no shadow, no floor plane, no reflection, no lighting variation."
- Demand "crisp clean edges and generous padding; the subject fully separated from the background."
- "Do not use #00ff00 anywhere in the subject."
- Choose a key the subject doesn't contain: default `#00ff00`; for green subjects use `#ff00ff`;
  avoid `#0000ff` for blue subjects. Pass the same hex to `to_rgba.py --key`.
- Avoid chroma-key for wispy edges (hair, fur, smoke, glass, fine foliage) — the cutout will fringe.
  Tell the user that true transparency for those needs the paid API path, which this skill avoids.

## Example expansions

**Request:** "icon for a meditation app"
**Prompt:** "A minimal app icon, flat geometric vector, centered composition: a single calm lotus
formed from soft overlapping petals, gentle indigo-to-teal gradient on a warm off-white rounded
square, subtle long shadow. Balanced, premium, modern. No text, no watermark."

**Request:** "/imagegen RGBA a cartoon avocado mascot giving a thumbs up"
**Prompt:** "A friendly cartoon avocado mascot with a happy face giving a thumbs up, bold clean
flat-illustration style, thick outlines, bright cheerful colors, full body, crisp clean edges with
generous padding, on a perfectly flat solid #00ff00 chroma-key background — one uniform color, no
shadow, no gradient, no floor, no reflection. Do not use #00ff00 anywhere on the avocado. No text,
no watermark." (then `to_rgba.py --key 00ff00`)
