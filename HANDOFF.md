# ship-ready — session handoff

**For:** the next agent picking this up fresh.
**Repo:** `/Users/mohamed/projects/ship-ready` — the `ship-ready` Claude Code skill (a `/ship-ready` orchestrator: grill → autonomous Workflow build/converge/gate → confirm-first ship). Bundle under `.skill/`.
**Branch:** `main`. **All session edits are UNCOMMITTED in the working tree.** Nothing has been committed or pushed.

---

## 0. TL;DR — where we are

1. We ran a multi-angle review of the skill → wrote `REVIEW.md`.
2. We **fixed the 5 High-severity findings** (H1–H5) + a bonus pre-existing crash bug. **These edits are DONE** (in `canonical-workflow.md`, `adaptation-layer.md`, `README.md`, `SKILL.md`), syntax-verified.
3. We then discovered the skill's **review phase reproduces a STALE version of `/code-review`** and pulled the **real, current built-in `/code-review` spec out of the Claude Code binary**.
4. **PENDING (not started):** refactor the review phase to mirror the *current* `/code-review` (angles + 3-state verify), split across ship-ready's two clocks. Architecture is agreed; **one decision is open** (Option A vs B, §6).

---

## 1. Verified Claude Code ground truth (don't re-verify — sourced)

| Fact | Verdict | Source |
|---|---|---|
| **Workflow tool is GA** (`agent()`/`parallel()`/`pipeline()`/`phase()`/`isolation`/`resumeFromRunId`) | TRUE, but **gated**: requires **Claude Code ≥ v2.1.154** + a **paid plan** | `code.claude.com/docs/en/workflows` |
| `resumeFromRunId` | Real, but an **Agent-SDK-level** param (`WorkflowInput`, SDK v0.3.149+), not a CLI feature | `code.claude.com/docs/en/agent-sdk/typescript` |
| **Nested subagents** | Shipped **v2.1.172**, **5-level** depth cap; prevent nesting by omitting `Agent` from a subagent's `tools` | `changelog`, `agent-sdk/subagents` |
| `disable-model-invocation: true` | Valid frontmatter; user-only invoke, description not in startup context | `code.claude.com/docs/en/skills` |
| Skill authoring rules | name ≤64 lowercase-hyphen + match dir; description ≤1024 chars, third-person, what+when; SKILL.md <500 lines; references one level deep | `platform.claude.com/docs/.../agent-skills/best-practices` |
| **Can a workflow phase-agent spawn subagents?** | **NO** — *not in docs* (undocumented), but **PROVEN EMPIRICALLY** this session (see §2) | empirical |

ship-ready passes the authoring rules (name 10 chars, desc 875 chars, SKILL.md 204 lines, progressive disclosure). The one gap: skills live under `.skill/` (a portable bundle), not the auto-discovered `.claude/skills/` — the README's `cp -R .skill/* ~/.claude/skills/` is the install step.

---

## 2. The empirical nesting test (we proved it, didn't infer it)

Ran two probes side by side:
- **Control — a normal subagent** (via `Agent` tool): HAS the `Agent` tool, spawned a sub-subagent, got `PONG`. ✅ Normal subagents nest.
- **A workflow agent** (spawned by `agent()` inside a Workflow): its literal toolset is **`Bash, Edit, Read, SendUserFile, Skill, ToolSearch, Write, StructuredOutput`** — **NO `Agent`/`Task`**, and `ToolSearch select:Task,Agent` → *"No matching deferred tools found."* It could not spawn anything.

**Conclusion (load-bearing for the architecture):** A workflow phase-agent **cannot fan out to subagents** — but it **CAN call `Skill`**. Therefore:
- `thermo-nuclear` (one self-contained skill, no fan-out) → runs as a real `Skill()` call inside one phase-agent. ✅
- `/code-review` (inherently fans out N reviewers) → **cannot** run inside a phase-agent at useful effort. The **workflow SCRIPT** must be the orchestrator (it has `agent()`/`parallel()`); the script reproduces the fan-out.

---

## 3. THE BIG DISCOVERY — the real built-in `/code-review`

**The skill reproduces the WRONG `/code-review`.** There are three different artifacts; only the third is real:
- ❌ `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/code-review/commands/code-review.md` — a **stale marketplace plugin** (5 Sonnet lenses: `claude-md/bugs/git-history/prior-prs/code-comments` + Haiku 0–100 confidence + **80-floor**). **NOT what runs.** (I mistakenly cited this mid-session — ignore it.)
- ❌ `workflow-review-phase/references/code-review-roster.md` — the skill's reproduction of that **stale plugin** (same lenses + 0–100/80-floor; also falsely claims "claude-md runs twice").
- ✅ **The built-in command, compiled into the binary** at `/Users/mohamed/.local/share/claude/versions/2.1.186`. **This is the real `/code-review`.**

### The real `/code-review` (v2.1.186), extracted from the binary

**Invocation:** `[low|medium|high|max|ultra] [--fix] [--comment] [<target>]`

**Phase 0 — diff:** `git diff @{upstream}...HEAD` (or `main...HEAD`/`HEAD~1`) + `git diff HEAD` for uncommitted; or a passed target (PR/branch/path). Skips test/fixture hunks at low effort.

**It fans out 10 finder angles** (via the **Explore** agent), each up to 8 candidates:

*5 correctness angles (verbatim prompts):*
- **A — line-by-line diff scan:** "Read every hunk in the diff, line by line. Then Read the enclosing function for each hunk — bugs in unchanged lines of a touched function are in scope. For every line ask: what input, state, timing, or platform makes this line wrong? Look for inverted/wrong conditions, off-by-one, null/undefined deref, missing `await`, falsy-zero checks, wrong-variable copy-paste, error swallowed in catch, unescaped regex metachars."
- **B — removed-behavior auditor:** "For every line the diff DELETES or replaces, name the invariant or behavior it enforced, then search the new code for where that invariant is re-established. If you can't find it, that's a candidate: a removed guard, a dropped error path, a narrowed validation, a deleted test that was covering a real case."
- **C — cross-file tracer:** "For each function the diff changes, find its callers (Grep for the symbol) and check whether the change breaks any call site: a new precondition, a changed return shape, a new exception, a timing/ordering dependency. Also check callees: does a parallel change in the same PR make a call unsafe?"
- **D — language-pitfall specialist:** "Scan for the classic pitfalls of the diff's language/framework — JS falsy-zero, `==` coercion, closure-captured loop var; Python mutable default args, late-binding closures; Go nil-map write, range-var capture; SQL injection; timezone/DST drift; float equality. Flag any instance the diff introduces."
- **E — wrapper/proxy correctness:** "When the PR adds or modifies a type that wraps another (cache, proxy, decorator, adapter): check that every method routes to the wrapped instance and not back through a registry/session/global — e.g. a caching provider holding a `delegate` field that resolves IDs via `session.get(...)` instead of `delegate.get(...)` will re-enter the cache or recurse. Also check that the wrapper forwards all the methods the callers actually use."

*5 quality angles (verbatim prompts):*
- **Reuse:** "Flag new code that re-implements something the codebase already has — Grep shared/utility modules and files adjacent to the change, and name the existing helper to call instead."
- **Simplification:** "Flag unnecessary complexity the diff adds: redundant or derivable state, copy-paste with slight variation, deep nesting, dead code left behind. Name the simpler form that does the same job."
- **Efficiency:** "Flag wasted work the diff introduces: redundant computation or repeated I/O, independent operations run sequentially, blocking work added to startup or hot paths. Also flag long-lived objects built from closures or captured environments — they keep the enclosing scope alive (a leak when it holds large values); prefer a class/struct that copies only the fields it needs. Name the cheaper alternative."
- **Altitude:** "Check that each change is implemented at the right depth, not as a fragile bandaid. Special cases layered on shared infrastructure are a sign the fix isn't deep enough — prefer generalizing the underlying mechanism over adding special cases."
- **Conventions (CLAUDE.md):** "Find the CLAUDE.md files that govern the changed code (user-level `~/.claude/CLAUDE.md`, repo-root, plus any CLAUDE.md/CLAUDE.local.md in an ancestor dir of a changed file). Read each, check the diff for clear violations. Only flag a violation when you can quote the exact rule and the exact line that breaks it — no style preferences, no vague 'spirit of the doc'. Name the CLAUDE.md path and quote the rule."

**Verify (Phase 2) — 3-state, NOT a 0–100 score:** dedup candidates (keep the most concrete failure scenario), then **one verifier per candidate** returning exactly **`CONFIRMED` / `PLAUSIBLE` / `REFUTED`**. Keep CONFIRMED+PLAUSIBLE, drop REFUTED. "**PLAUSIBLE by default**" in recall mode — don't refute for being "speculative" when the state is realistic (races, nil on rare path, falsy-zero, off-by-one, retry storms, lost regex anchor). REFUTED only when constructible from the code (factually wrong / provably impossible / already guarded in this diff / pure style).

**Sweep (Phase 3):** one fresh finder with the verified list, hunting ONLY for gaps not already listed.

**Output:** JSON array `{file, line, summary, failure_scenario}`, ranked most-severe first, capped. Correctness outranks cleanup when the cap forces a cut.

**Effort tiers:**
- `low` → 1 inline diff pass, **no subagents**, no verify, ≤4 findings.
- `high`/`max` → `5+5 angles × 8 candidates → 1-vote verify → sweep → ≤15 findings`, recall-biased ("a missed bug ships").
- `ultra` → "**deep multi-agent review in the cloud (requires claude.ai account)**" — the router (`M4m`) emits `Invoke: Workflow({ name… })`; it runs the **same finder angles + verify pass** in a background workflow. (Anthropic's own proof that code-review-in-orchestration = a script/workflow fan-out.)

### How to re-extract (if you need the raw text again)
Binary: `/Users/mohamed/.local/share/claude/versions/<latest>`. The angle texts are JS string literals. Symbols: `amt`(phase0), `_Za`/`yZa`/`TZa`/`SZa`/`bZa`(correctness A–E), `lmt`+`Z_o`(reuse), `Jxe`(simplification), `Xxe`(efficiency), `Qxe`(altitude), `cmt`(conventions), `eyo`/`tyo`(verify verdicts), `i4p`(sweep), `ryo`(output), `CZa`(low), `vZa`(high/max), `AZa`/`s4p`(verify phases), `M4m`/`N4m`(ultra routing). Extract with a Python byte-window around `b'removed-behavior'`, `b'5+5 angles'`, `b'deep multi-agent review'`.

---

## 4. The original review (`REVIEW.md`) — findings status

Full report is in `REVIEW.md`. 35 raw findings → 16 verified → 14 stood. Status after this session:

- **C1 (Critical) — undisclosed Workflow version/plan floor + `.skill/` install path.** ⚠️ **NOT yet fixed.** Should add "Requires Claude Code ≥ 2.1.154 + paid plan" and the `.skill/`→`.claude/skills/` step to SKILL.md/README.
- **H1–H5** — ✅ **all fixed this session** (see §5).
- **Mediums M1–M6** — mostly addressed by the H5/H3 fixes (LENS_DEF closes M1/M2 within ship-ready; untestable guard closes M4-ish). Doc dedup (README guardrails M5) and cost-framing (M6) **not done**.
- **2 findings were adversarially OVERTURNED** (a "resume-unsafe loop" false alarm) — documented in REVIEW.md so they're not re-chased.

---

## 5. What was CHANGED this session (DONE, uncommitted)

All five High fixes + a bonus. Files:

**`.skill/ship-ready/references/canonical-workflow.md`** — full rewrite of the script (`+395/−128`):
- **H1:** `implementInDagOrder` now has a real body (wave-based DAG execution, returns `{target→result}`). Was "paste verbatim" with NO body.
- **H2:** converge loop is now **per-target** — extracted `convergeTarget(t, disposed, cursorMap, pass)`; added `integrationPass()` (multi-repo seam review→triage→fix) + integration gate (`commands.contract` tier-1); **per-target** disposition caches + delta cursors; single-repo collapses to identical old behavior. Was hardwired to `targets[0]`.
- **H3:** `test-integrity` lens (lap-1 always; `test`/`spec` fileLensMap rows) flags tautological `@AC` tests; script-owned `MAX_UNTESTABLE_RATIO` (0.34) downgrades `ship`→`needs-human`.
- **H4:** `OPEN_QUESTION` schema threaded through `PLAN`/`IMPL_RESULT`; early `needs-human` exit BEFORE the converge loop on a blocking mid-build unknown.
- **H5:** `LENS_DEF` registry = single source of truth for every lens key + oracle prompt; `SURFACE_LENS` reconciled to `infra-safety`/`a11y`+`visual-state`/`public-api`.
- **BONUS:** fixed a **pre-existing missing-brace bug in the `LEDGER` schema** (5 nesting levels, only 4 closes) that would have crashed any real run. Found by `node --check`. **Verify with:** extract the `js` blocks, wrap in `async function main(){…}`, strip `export`, `node --check`.

**`.skill/ship-ready/references/adaptation-layer.md`** — §3 `claude-md`-lens line fixed (it's cut from the gate); §4 table keys normalized + `test-integrity` added; `fileLensMap` test/spec rows; §5 untestable-ratio + test-integrity note.

**`.skill/ship-ready/SKILL.md`** — reality-anchored-lenses bullet (added `test-integrity`/`LENS_DEF`), completeness guardrail (test-integrity + untestable ratio), new mid-build-ambiguity guardrail.

**`README.md`** — `visual/state` → `visual-state`.

**`REVIEW.md`** — the original review report (new file).

---

## 6. PENDING WORK — the review-phase refactor (agreed design, NOT started)

**Goal:** replace the stale `/code-review` reproduction with the **current** built-in's engine (§3), wrapped in ship-ready's loop. Mirror at the **script level** (a phase-agent can't fan out — §2); the angle texts are now known verbatim, so the inheritance is faithful, not approximate.

**Agreed architecture — split the real `/code-review` across ship-ready's two clocks:**

```
Mechanism A (BLOCKING — correctness): script-level parallel() of
   the 5 correctness angles A–E (verbatim from §3)
   ⊕ ship-ready's surface-gated additions /code-review lacks:
       security (authz/IDOR/secrets), concurrency (races/locks),
       data-integrity (migration/atomicity), integration (multi-repo), test-integrity (completeness)
   → 3-state verify (CONFIRMED/PLAUSIBLE/REFUTED, verbatim) → sweep (lap 1)
   → Opus triage = THE GATE → fix → re-derive diff → delta-scoped re-review (disposition memory)
   → mechanical AC-test gate. Loop until script says clean.

Mechanism B (ADVISORY — cleanliness, never blocks): 
   thermo-nuclear Skill() ⊕ /code-review's quality angles (reuse/simplification/efficiency/altitude/conventions)
   → triage (cheap wins only) → fix-or-ledger.
```
Effort scales like the real tool (low = 1 pass ≤4; high/max = 10×8 → verify → sweep ≤15).

**Files to touch:**
1. `workflow-review-phase/references/code-review-roster.md` — **rewrite**: replace stale lenses + 0–100/80-floor with the current angles + **3-state verify** + sweep (§3).
2. `.skill/ship-ready/references/canonical-workflow.md` — rewire Mechanism A review to the correctness angles + 3-state verify + sweep; move quality angles into Mechanism B alongside thermo-nuclear. (`LENS_DEF` from H5 is the place to host the verbatim angle prompts.)
3. `SKILL.md` + `README.md` — correct the "reproduces `/code-review`" claims to: *"mirrors the **current** built-in `/code-review` angles + 3-state verify at the script level (a phase-agent can't fan out); thermo-nuclear runs as a `Skill` call."* Drop any "claude-md runs twice" / 80-floor language.

**⚠️ THE ONE OPEN DECISION (ask the user before implementing):**
- **Option A (recommended):** keep the Workflow + mirror the angles at script level. Preserves the **script-decided gate** (ship-ready's core property).
- **Option B:** abandon the Workflow loop for a top-level `Agent` orchestrator (which CAN nest, v2.1.172) and literally `Skill`-call the real `/code-review`. Inherits Anthropic's maintenance, but **loses the script-computed gate** (a model decides "done"). Not recommended.

The user was about to choose. **Confirm A vs B before writing code.**

---

## 7. Critical gotchas for the next agent

- **Frozen-mechanism rule:** in `canonical-workflow.md`, the orchestrator fills ONLY the CONFIG block and pastes the mechanism VERBATIM. Any fix must land in the frozen mechanism, never require the orchestrator to hand-write logic (that's the H1 footgun class).
- **Workflow phase-agents cannot spawn subagents** (proven). thermo-nuclear = `Skill()` call; code-review = script-level `parallel()`. Don't try to nest.
- **`/code-review` truth lives in the binary**, not the marketplace plugin and not the skill's roster. Both of those are stale.
- **Syntax-check any `canonical-workflow.md` script edit**: extract the ```js blocks, wrap in an async function, strip `export`, `node --check`. Top-level `await`/`return` are valid in the runtime (the body is an async fn) but need the wrapper to check locally.
- **Nothing is committed.** Decide with the user whether to commit (branch off `main` first per repo convention) once the refactor lands.
- **Design philosophy the user holds:** review's prior objective is *find every bug (by tracing paths, since they often can't run tests — no Docker/PG/Flutter device) + every smell*; tests run when they can but review is the bug engine; "zero tech debt" = "zero **silent** debt" (fixed-or-ledgered). Don't over-index on "mechanize everything" — they pushed back on that.

---

## 8. Recommended next steps (in order)
1. Confirm **Option A vs B** (§6) with the user.
2. Implement the review-phase refactor (§6) — rewrite `code-review-roster.md`, rewire Mechanism A/B, fix the claims.
3. Address **C1** (version/plan/install disclosure) — cheap, high-value.
4. (Optional) M5 README guardrail dedup, M6 cost-framing note.
5. Syntax-check, then ask about committing.
