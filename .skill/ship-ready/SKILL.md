---
name: ship-ready
description: >-
  Turn any unit of work — a freeform feature request OR a Jira/Linear/GitHub issue — into ship-ready,
  reviewed, tested code with no bugs and no tech debt. Grill requirements to zero ambiguity and detect the
  project (stack/commands/conventions) at intake, then run one autonomous Workflow: plan, research, implement,
  converge on correctness+completeness behind a machine gate, take ONE advisory maintainability pass, and emit
  a structured ship verdict. Project-agnostic — backend, frontend, full-stack, mobile (incl. Flutter), CLI,
  library, or infra; monolith or microservices; one repo or a feature spanning several. Invoke it to build,
  implement, ship, deliver, or finish a feature, or to work a ticket/issue end to end (e.g. "build the X
  feature", "work ABC-123", "take this to a merge-ready PR") — for a whole unit of work, not a one-line edit,
  a review, or a pure question.
disable-model-invocation: true
---

# ship-ready

Turn a unit of work into code you'd actually merge — correct, tested, reviewed, idiomatic, and complete
against its acceptance criteria — without a human babysitting the middle, and **without the loop burning
tokens re-checking work that's already clean.** This skill is a **universal orchestrator**: it detects the
project it's running in and adapts, instead of assuming any stack, shape, or toolchain.

The headline idea: **resolve all ambiguity up front with an interview, then run an autonomous build that
converges on correctness behind a machine gate — and treats code-cleanliness as advice, not a gate.** A human
is in the loop in exactly two places: the grilling at the start, and a confirm before anything outward
(commit / PR / ticket write) at the end. Everything between is autonomous and structurally gated.

## The shape (three stages)

```
INLINE  ── Intake → GRILL (grill-me) → PRD (WHAT) + ProjectProfile (detected here) → save .prd/ ──┐
                                                          (the only human-facing stage)            ▼  author Workflow (CONFIG inlined)
WORKFLOW ── Plan → Research → Implement → ⟲ A: converge(correctness+completeness) → B: polish×1 (advisory) → Ship-gate ──┐
                                                              (one Workflow, autonomous, machine-gated)                  ▼
INLINE  ── present ShipVerdict (+ simplifications ledger) → confirm-first commit / PR / ticket write-back
```

Two things changed from the obvious design, both because a real run proved them wasteful:

- **There is no separate "Adapt" phase.** The inline agent is already reading the repo to grill it, so it
  produces the `ProjectProfile` *there* and inlines it as Workflow config. (Detection-as-a-phase only survives
  for multi-repo targets the inline stage didn't read.)
- **The "loop until clean" is split into two clocks.** Correctness+completeness *converge fast and gate*;
  maintainability/DRY is *bottomless and must not gate*. So **Mechanism A** converges the first; **Mechanism B**
  is a single non-blocking polish pass that emits an advisory ledger.

Depth lives in `references/` — read the one for the stage you're in.

## Non-negotiable: grill first

**Always run `grill-me` before anything else** — it is the load-bearing reason the rest can be autonomous. A
Workflow phase-agent cannot stop to ask the user a question mid-run, so every ambiguity has to die before the
Workflow starts:

```
Skill({ skill: 'grill-me' })
```

`grill-me` runs a `/grilling` session under the hood; it's normally-invocable, so call it via the Skill tool.
(ship-ready itself is `disable-model-invocation`: the **user** starts it with `/ship-ready`.) Seed it with
everything you know (ticket body, request, repo scan) so it targets real gaps. It self-scales. It must nail:
**scope**, **the target set** (which repos/services, each with a local path), **repo integrity** (does each
target build *today* — missing imports/config are in-scope work, not gate surprises), the **contracts** between
targets, **acceptance criteria**, and **non-obvious constraints**.

## Intake also produces the ProjectProfile (no Adapt phase)

While grilling, the inline agent is already reading the repo — so **detect the `ProjectProfile` here** and inline
it into the Workflow config: stack, package manager, the **real gate commands read from CI as ground truth**,
**which commands actually exist** (so a missing lint script becomes `not-applicable`, never a phantom gate
failure), conventions (the sibling modules to mirror), surfaces, and a `file→lens` map. Detail:
`references/adaptation-layer.md`. For multi-repo, splice a lean parallel Adapt into the Workflow only for targets
not profiled at intake.

## Synthesize the PRD (pure WHAT) — with testable criteria

Synthesize the interview into a lean, business-level PRD and **save it to `.prd/<slug>.md`**. Pure **WHAT, not
HOW**: problem, solution, user stories, acceptance criteria, scope, systems touched. Technical planning
(contracts, interfaces, sequencing) stays in the Workflow's Plan so it's decided once. (We write our own PRD;
we don't pull Pocock's *technical* `to-prd`.)

- **`acceptanceCriteria` in EARS form**, numbered `AC1..ACn`. Each AC will be mapped to **≥1 test assertion** in
  Implement, so completeness is **machine-checked by running the AC-tagged tests** — not re-judged by an agent
  every loop. Where a criterion genuinely can't be asserted on this stack, it's flagged `untestable` and the
  ship-gate judges it (it never silently passes).
- **Systems touched** — the repos/services the work spans (each with its local path). One system ⇒ the
  multi-repo machinery collapses away.

Then author the Workflow, filling **only the CONFIG block** (`prdPath`, `targets` *with their profiles*,
contracts, caps) and pasting the mechanism verbatim. Don't use the `args` channel — a stringified/empty `args`
crashes the script on first access, and inlining is resume-safe.

## Stage 2 — the canonical Workflow (autonomous)

Launch **one** Workflow from the template in `references/canonical-workflow.md`. It is a **frozen mechanism +
a CONFIG block**: you fill config, you paste the loop/predicate/disposition-cache/gate verbatim (re-deriving
them per run is what produced the historical footguns). Phases:

1. **Plan** — (multi-repo) freeze the contracts + dependency DAG, then per-target plans; **map each AC to a
   concrete test assertion**. Conform to each repo's conventions — *the code is the oracle; CLAUDE.md is a hint
   and the code wins on conflict.*
2. **Research** — current best practices for the *actual* libraries via **Context7**, reconciled with repo
   conventions, so review isn't fighting nonidiomatic code later.
3. **Implement** — per target in DAG order, against the frozen contract. **Build lazy (YAGNI):** stdlib →
   native → installed dep → one line → only then new code; no unrequested abstractions; never simplify away
   validation/error-handling/security/PRD requirements. **Mirror the sibling code.** Write the AC-tagged tests.
   Mark deliberate shortcuts with a `ponytail: <ceiling>, <upgrade>` comment.
4. **Mechanism A — converge correctness + completeness** (the gate; see below).
5. **Mechanism B — one advisory polish pass** (maintainability; never gates; see below).
6. **Ship-gate** — a final agent emits a structured `ShipVerdict`.

Return the `ShipVerdict` so the inline stage can branch on it.

### Mechanism A — converge correctness + completeness (the real gate)

A loop of **Stage → Review → Triage → Fix → Gate**, where **the script (not a model) decides whether to loop
again.** What makes it converge fast *and* without waste:

- **Delta- and surface-scoped review.** Pass 1: the focused fan-out over the surfaces present. Pass 2+: review
  **only the files the last fix changed**, with **only the lenses whose surface those files touch.** (A DRY-only
  fix re-runs no security/data reviewers.) Review is `parallel()` in the script; thermo-nuclear is **not** in
  this loop (it's Mechanism B).
- **Reality-anchored lenses only.** `bugs` always; `api-contract`/`security`/`data-integrity`/`concurrency`
  surface-gated; `git-history` only on modified pre-existing code. The artifact-anchored lenses are gone from
  the gate (see *Guardrails*).
- **Incremental triage with memory.** A `disposed` cache carries verdicts across passes; **only new findings
  reach triage.** This stops the loop re-litigating the same nits (and re-accepting a finding it earlier
  rejected). **Triage is the gate** — keyed off `accepted == 0`, never a confidence score.
- **A mechanical, N/A-aware gate + test-backed completeness.** Tier-0 (typecheck/lint/format/unit) always; tier
  1/2 if present; **plus the AC-tagged tests** (completeness folded in — no separate coverage agent). The agent
  *reports* per-gate status (`passed/failed/skipped/not-applicable`); the **script computes `green`**: a missing
  command is `not-applicable` and never blocks, a tier-0 command the env can't run is `failed` and never
  silently green.
- **Exit (harness-owned, fail-safe):** `accepted == 0` **and** tier-0 actually passed **and** no AC test is
  failing. Positive evidence required — a null/empty result reads as *not* clean. Cap is a backstop; the
  predicate exits first. Hitting the cap returns `blocked` with residuals — never a silent green.

### Mechanism B — the advisory polish pass (one, non-blocking)

After A is green, run maintainability **once**: thermo-nuclear + `yagni`/simplify on the full diff, plus a
**doc-drift** check (CLAUDE.md/comments the code now contradicts — the code is right, the doc is stale). Apply
the cheap, obviously-worth-it cleanups (DRY extractions), re-verify tier-0, and **roll everything else into an
advisory ledger** on the verdict: the `ponytail:` markers (with ceiling + upgrade trigger), deferred findings,
and drift notes. This is **accepted, tracked debt** — it does not gate the exit (a clean run ships with it
listed), it just keeps a deferral from silently becoming permanent.

## Stage 3 — confirm-first close-out

Present the `ShipVerdict` (with its simplifications ledger). Then, **only with confirmation**, perform outward
actions: commit / push / open a PR, and (for ticket work) post a summary and transition status. Drafting is
fine; publishing is outward-facing and needs an explicit go. `blocked` / `needs-human` stop here and surface
exactly what's unresolved (`needs-human` *resumes* the Workflow via `resumeFromRunId`, it doesn't restart).

## Model usage — assess per phase, don't hardcode

Choose each phase's model/effort by **stakes × complexity × blast-radius**; the table in
`references/canonical-workflow.md` is a *prior*. Deep judgment (plan, security/data/concurrency lenses, triage,
ship-gate) → top tier; implement → top tier (codegen is the product); fix/research → mid; gate/re-verify/stage →
cheap. Escalate mid-loop if signal demands it.

## Guardrails (load-bearing — keep them)

- **Grill first, always.** No skipping to implementation, however clear the request looks.
- **Two clocks: gate correctness, advise on cleanliness.** Correctness+completeness block ship; DRY/maintainability
  never does — it's one capped pass plus a ledger. Don't let the bottomless axis hold the cheap one hostage.
- **Triage is the gate, never a threshold — and it has memory.** Every *new* finding goes to triage; dispositioned
  findings never re-enter. The strongest agent decides; a score floor lets the weakest silently kill a real one.
- **Review the delta, not the world.** After pass 1, review only what the last fix changed, with only the
  surface-relevant lenses. Re-scanning unchanged code is the single biggest measured waste.
- **A lens is only as good as its oracle.** Keep lenses that judge the code against execution semantics
  (`bugs`/`api-contract`/`security`/`data-integrity`/`concurrency`). Drop the ones anchored on lagging artifacts:
  `prior-prs` (unrelated/hallucinated in a team), `code-comments` (comments rot), and `claude-md` *as a gate*
  (docs lag the code). Enforce conventions by **prevention** (Implement mirrors the sibling code; code wins over
  CLAUDE.md); surface doc/comment **drift** as an advisory note, not a finding.
- **Completeness is test-backed.** Each AC has ≥1 tagged assertion; the gate runs them. Untestable criteria defer
  to the ship-gate, flagged — never a silent pass.
- **The gate is mechanical and honest about N/A.** Real commands run; the script computes `green`; a command that
  doesn't exist is `not-applicable` (never blocks); a tier-0 command the env can't run is `failed` (never green).
- **Re-derive the diff from git each pass.** Trust git, not a fix-agent's reported file list. In a worktree,
  `git add -A` before diffing.
- **Frozen mechanism, config-only authoring.** Fill the CONFIG block; paste the loop/predicate/cache/gate verbatim.
- **A non-building repo is never done; `needs-human` resumes; confirm before any outward write.**

## Dependencies (deliberately lean — don't add skills)

Hard dependencies, all present: **`grill-me` + `grilling`** (the interview), **Context7** (library docs, an MCP),
and the review stack — **`workflow-review-phase`** (the spliced review→triage→fix interior),
**`thermo-nuclear-code-quality-review`** (Mechanism B), and the **`/code-review`** engine it reproduces.
Everything else (superpowers, cc-sdd, Pocock's `tdd`/`diagnosing-bugs`, Pact/Specmatic) is
**detect-and-use-if-present**, never installed. Patterns we liked are *encoded here, not pulled in as skills*:
spec-coverage reconcile, EARS, contract-first, repro→root-cause debugging, and
[`ponytail`](https://github.com/DietrichGebert/ponytail)'s YAGNI ladder + deliberate-simplification ledger
(the `yagni` lens, the lazy-build clause in Implement, and the `ponytail:`-marker harvest).

## Reference files

- `references/intake-and-spec.md` — grill-me handoff, ticket adapters, **ProjectProfile detection at intake**,
  PRD synthesis (pure-WHAT, `.prd/<slug>.md`), EARS criteria + **AC→test mapping**, confirm-first write-back.
- `references/adaptation-layer.md` — project detection, CI-as-ground-truth, the **oracle-reliability lens ranking**,
  the surface→lens map, `cmdExists`/tiered gates, and the optional `.claude/ship-ready.json` cache.
- `references/canonical-workflow.md` — the v2 Workflow template: CONFIG + frozen mechanism, schemas, **Mechanism A
  (converge) and B (polish)**, the disposition cache, delta-scoping, the mechanical gate, and the model-tier prior.
- `references/multi-repo-contracts.md` — the WorkGraph, contract-first two-level planning, per-target fan-out, the
  integration lens, and how a single repo collapses the machinery.
