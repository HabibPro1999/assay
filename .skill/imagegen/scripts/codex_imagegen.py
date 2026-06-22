#!/usr/bin/env python3
"""Generate ONE image with GPT-image-2 via Codex's built-in image_gen tool and save it to a real PNG.

Why this exists
---------------
Codex's built-in `image_gen` tool runs on the user's ChatGPT/Codex subscription — no
OPENAI_API_KEY, no per-image API charge. But under headless `codex exec` it does NOT write a
file to ~/.codex/generated_images/; the PNG comes back inline as base64 at `payload.result` of an
`image_generation_call` record in the session rollout JSONL. This script forces the native tool,
captures the printed `session id`, then decodes that base64 into the output file.

Usage
-----
  codex_imagegen.py --out path/to/image.png --prompt "a detailed prompt ..."
  echo "a detailed prompt" | codex_imagegen.py --out path/to/image.png
  codex_imagegen.py --out img.png --prompt-file prompt.txt --timeout 480

The prompt should be the full image description WITHOUT the leading "$imagegen" — this script
adds the "$imagegen " prefix and the hard rules that force the subscription-backed native tool.
"""
import argparse, base64, glob, json, os, re, subprocess, sys

# Hard rules: without these, the codex agent tends to "helpfully" fall back to rendering the image
# with PIL/SVG (deterministic but not gpt-image-2) or to the API-key CLI (which costs money). We
# explain *why* each constraint matters so the agent cooperates instead of working around it.
RULES = """

----
HARD RULES (follow exactly):
- You MUST use your built-in image_gen tool (gpt-image-2). It runs on the ChatGPT subscription and is the only acceptable method here.
- Do NOT write or run any code. No python, PIL/Pillow, SVG, HTML, matplotlib, cairo. Do NOT use scripts/image_gen.py. Do NOT set or use OPENAI_API_KEY (that path bills per image and is forbidden).
- Generate exactly ONE image. Render any text in the image crisply and spelled exactly as given.
- Just call the native image_gen tool once. Do not edit, create, or move any files. That is the entire task.
"""

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def run_codex(prompt: str, timeout: int) -> str:
    prompt = prompt.strip()
    if not prompt.lower().startswith("$imagegen"):
        prompt = "$imagegen " + prompt
    full = prompt + RULES
    try:
        proc = subprocess.run(
            ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "-"],
            input=full, text=True, capture_output=True, timeout=timeout,
        )
    except FileNotFoundError:
        sys.exit("codex CLI not found on PATH. Install Codex CLI and run `codex login`.")
    except subprocess.TimeoutExpired:
        sys.exit(f"codex exec timed out after {timeout}s")
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def find_session_id(out: str):
    for line in out.splitlines():
        if "session id" in line.lower():
            m = UUID_RE.search(line)
            if m:
                return m.group(0)
    m = UUID_RE.search(out)
    return m.group(0) if m else None


def find_rollout(session_id: str):
    pat = os.path.expanduser(f"~/.codex/sessions/**/rollout-*{session_id}*.jsonl")
    hits = glob.glob(pat, recursive=True)
    return max(hits, key=os.path.getmtime) if hits else None


def extract_last_image_b64(rollout: str):
    results = []
    with open(rollout) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            p = obj.get("payload") or {}
            if p.get("type") == "image_generation_call" and p.get("result"):
                results.append(p["result"])
    return results[-1] if results else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--prompt", help="image prompt (without the $imagegen prefix)")
    ap.add_argument("--prompt-file", help="read the prompt from a file")
    ap.add_argument("--timeout", type=int, default=480, help="seconds to wait for codex (default 480)")
    a = ap.parse_args()

    if a.prompt_file:
        prompt = open(a.prompt_file).read()
    elif a.prompt:
        prompt = a.prompt
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        sys.exit("empty prompt")

    out = run_codex(prompt, a.timeout)
    sid = find_session_id(out)
    if not sid:
        sys.stderr.write(out[-1500:] + "\n")
        sys.exit("could not find a session id in codex output (did codex run?)")
    rollout = find_rollout(sid)
    if not rollout:
        sys.exit(f"no rollout file found for session {sid}")
    b64 = extract_last_image_b64(rollout)
    if not b64:
        sys.exit(
            f"no image found in rollout for session {sid}.\n"
            "The model likely refused or fell back instead of calling image_gen. "
            "Re-run; if it persists, simplify the prompt or check `codex login`."
        )
    dest = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(base64.b64decode(b64))
    print(dest)


if __name__ == "__main__":
    main()
