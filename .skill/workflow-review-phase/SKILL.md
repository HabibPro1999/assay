---
name: workflow-review-phase
description: >-
  Emits a ready-to-splice Workflow review→triage→fix segment that runs BOTH a thermo-nuclear
  code-quality review (a real Skill call inside a phase-agent) AND a code-review multi-lens fan-out
  (workflow-native parallel agents with verbatim 0–100 confidence scoring), then triages real-vs-noise
  and fixes the surviving findings against the diff. Use this WHENEVER you are authoring or editing a
  Workflow (the Workflow tool / an "ultracode" run) and need a review phase — when the user says "add the
  review phase", "use the review skill as a phase", "review and fix the diff in the workflow", "run
  thermo-nuclear and code-review", or otherwise wants the changed code reviewed and fixed inside an
  orchestration. Also use for a standalone (non-workflow) review of a branch diff via the nested-subagent
  mode. Prefer this over hand-rolling review agents: it encodes the validated runtime mechanics (a workflow
  phase-agent CAN invoke a skill but CANNOT spawn subagents, so thermo-nuclear runs as a real Skill call
  while code-review must be a script-level parallel() fan-out) and the correct per-stage model tiers.
---

# Workflow Review Phase

This skill gives you a **drop-in Workflow segment** that reviews a diff with two complementary engines,
keeps only the findings that survive scrutiny, and fixes them — all as deterministic `phase()` steps you
splice into whatever Workflow you are writing.

It is a **recipe**, not a runner. Your deliverable when this skill triggers is correct workflow JavaScript
appearing in the script you are authoring (or a complete standalone script), with the rubrics below wired in.

## Why it is shaped this way (validated, not assumed)

A probe across all workflow agent types established two facts that dictate the design:

1. **A workflow phase-agent CAN invoke the `Skill` tool.** So `thermo-nuclear-code-quality-review` — which
   is a self-contained rubric needing no helpers — runs faithfully as a *real Skill call inside one
   phase-agent*. Don't reimplement it; call it.
2. **A workflow phase-agent CANNOT spawn its own subagents** (no `Agent`/`Task` tool in any agent type).
   `code-review` fans out to many independent reviewers + confidence scorers, so it **cannot** run inside a
   single phase-agent — it would stall or silently collapse to one in-context pass. Therefore code-review is
   reproduced as the **workflow script's own `parallel()` fan-out**, where the script (not a phase-agent) is
   the orchestrator. The reviewer roster and the verbatim confidence rubric live in
   `references/code-review-roster.md`.

Keep these two mechanics exactly. They are the whole reason the segment is split the way it is.

## Parameters (decide these at the splice site)

| Param | Default | Meaning |
|---|---|---|
| `DIFF` | `'develop...HEAD'` plus uncommitted | What to review. A git range, or the changed-file list from a preceding implement phase (e.g. `impl.filesChanged`). |
| `VERIFY_CMD` | project typecheck + unit tests (e.g. `rtk pnpm typecheck && rtk pnpm -r test`) | Used to confirm fixes; integration/Docker suites excluded unless asked. |
| `SCOPE` | `'review+fix'` | `'review'` stops after triage and returns findings; `'review+fix'` also applies + re-verifies. |
| `LENSES` | the 7 in the roster | Which code-review lenses to fan out. Dial down for small diffs, up for audits. |
| `SCORE_FLOOR` | `null` (off) | **Optional** pre-triage noise filter, for LARGE audits only. `null` = skip scoring; send every lens finding straight to triage (the real gate). When set (~`25`), run the Haiku scorer and drop only findings below it (strips near-certain false positives) while attaching `confidence` as a signal for triage. Never a quality bar — triage is the gate, not the score (a strict floor silently kills real findings before the smartest agent sees them; in testing a real `78` was dropped by a floor of `80`). |
| `MODELS` | the table below | Per-stage model override. |

## Model tiers (defaults — Opus on the judgment, cheap on the mechanical)

| Stage | Model | Why |
|---|---|---|
| Thermo-nuclear review | **opus** | Deep maintainability judgment + ambitious "code-judo" restructuring. The important one. |
| Code-review · security lens | **opus** | High-stakes reasoning; a missed authz/secret is costly. |
| Code-review · concurrency lens | **opus** | Lock-ordering / race reasoning is subtle; worth the tier. |
| Code-review · other lenses (5) | **sonnet** | Faithful to `/code-review` (Sonnet reviewers); breadth over depth. |
| Confidence scoring *(optional)* | **haiku** | Off by default. Runs only when `SCORE_FLOOR` is set (large audits) — a cheap noise-strip + confidence signal, NOT a gate. |
| Triage (real-vs-noise, dedupe) | **opus** | Decides what actually gets changed; the second important judgment gate. |
| Fix-apply ("impl") | **sonnet** | Implementation work — competent codegen from a precise finding. |
| Re-verify | **haiku** | Runs the verify command and reports pass/fail. |

Override per call via `opts.model`; never hardcode a tier that contradicts this table without a reason.

## The segment (splice this into your Workflow script)

Define the schemas once near the top of your script, then paste the phases where the review belongs —
**after** whatever produced the diff (an implement phase, or just the current branch). Read
`references/code-review-roster.md` for `reviewerPrompt(lens)` and the verbatim `scorerPrompt(finding)`, and
`references/thermo-nuclear-rubric.md` for the fallback rubric if the skill isn't installed.

```js
// ── SCHEMAS (define once) ───────────────────────────────────────────────
const FINDINGS = { type:'object', additionalProperties:false, required:['findings'], properties:{
  findings:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['title','file','severity','category','rationale'], properties:{
      title:{type:'string'}, file:{type:'string'}, line:{type:['number','null']},
      severity:{enum:['low','medium','high','critical']}, category:{type:'string'},
      rationale:{type:'string'}, suggestedFix:{type:'string'} } } } } }
const SCORE = { type:'object', additionalProperties:false, required:['confidence','verdict'],
  properties:{ confidence:{type:'number'}, verdict:{type:'string'} } }
const TRIAGE = { type:'object', additionalProperties:false, required:['accepted','rejected','summary'],
  properties:{ accepted:{type:'array',items:FINDINGS.properties.findings.items},
    rejected:{type:'array',items:{type:'object',additionalProperties:false,
      required:['title','reason'],properties:{title:{type:'string'},reason:{type:'string'}}}},
    summary:{type:'string'} } }
const FIXED = { type:'object', additionalProperties:false, required:['applied','verified','filesChanged','notes'],
  properties:{ applied:{type:'array',items:{type:'string'}}, verified:{type:'boolean'},
    filesChanged:{type:'array',items:{type:'string'}}, notes:{type:'string'} } }

// ── INPUTS (set at the splice site) ─────────────────────────────────────
const DIFF = 'develop...HEAD'                    // or: impl.filesChanged.join(', ')
const VERIFY_CMD = 'rtk pnpm typecheck && rtk pnpm -r test'
const SCOPE = 'review+fix'
const SCORE_FLOOR = null                          // null = no pre-filter; triage is the gate. Set ~25 ONLY for large audits.
const LENSES = [                                  // {key, model} — see roster for prompts
  {key:'claude-md', model:'sonnet'}, {key:'bugs', model:'sonnet'},
  {key:'git-history', model:'sonnet'}, {key:'prior-prs', model:'sonnet'},
  {key:'code-comments', model:'sonnet'}, {key:'security', model:'opus'},
  {key:'concurrency', model:'opus'},
]

// ── REVIEW · thermo-nuclear (REAL Skill call inside one phase-agent) ─────
phase('Review · thermo-nuclear')
const tn = await agent(
  `Invoke the Skill tool now: Skill({ skill: 'thermo-nuclear-code-quality-review' }). Apply its standards `
  + `to the diff (${DIFF}); read the changed files and the surrounding code they touch. If that skill is not `
  + `available, apply the rubric in references/thermo-nuclear-rubric.md of the workflow-review-phase skill. `
  + `Return every maintainability/structure finding as the schema (severity reflects how much it hurts the `
  + `codebase; prefer findings that delete complexity).`,
  { label:'review:thermo-nuclear', phase:'Review · thermo-nuclear', model:'opus', effort:'high', schema: FINDINGS },
)

// ── REVIEW · code-review (script-level fan-out — phase-agents can't nest) ─
phase('Review · code-review')
const reviewed = await parallel(LENSES.map(l => () =>
  agent(reviewerPrompt(l.key, DIFF), { label:`review:${l.key}`, phase:'Review · code-review', model:l.model, schema: FINDINGS })))
let candidates = reviewed.filter(Boolean).flatMap(r => r.findings)
// OPTIONAL noise filter — runs ONLY for large audits (SCORE_FLOOR set). Triage is the real gate, so by
// default EVERY finding goes through. A hard score-gate here lets the weakest agent (Haiku) silently kill
// real findings before Opus triage ever weighs them — observed in testing: a real `78` dropped by a floor
// of `80`. When enabled, use ~25 to strip only near-certain false positives and keep `confidence` as a signal.
if (SCORE_FLOOR != null) {
  candidates = (await parallel(candidates.map(f => () =>
    agent(scorerPrompt(f, DIFF), { label:'review:score', phase:'Review · code-review', model:'haiku', schema: SCORE })
      .then(s => ({ ...f, confidence: s?.confidence ?? 0 })))))
    .filter(Boolean).filter(f => f.confidence >= SCORE_FLOOR)
}

// ── TRIAGE (dedupe + real-vs-noise against the diff — THE GATE) ──────────
phase('Triage')
const allFindings = [ ...(tn?.findings ?? []), ...candidates ]
const triaged = await agent(
  `Triage these review findings against the diff (${DIFF}). Dedupe overlaps (thermo-nuclear and code-review `
  + `often flag the same line from different angles — merge them). Drop anything that is a pre-existing issue, `
  + `a nitpick a senior engineer wouldn't raise, or something a typechecker/linter/CI already catches. Keep `
  + `only findings that are real, in-diff, and worth changing. Findings:\n${JSON.stringify(allFindings, null, 2)}`,
  { label:'triage', phase:'Triage', model:'opus', effort:'high', schema: TRIAGE },
)
if (SCOPE === 'review') return { findings: triaged, fixed: null, green: null }

// ── FIX (apply accepted findings coherently → re-verify) ────────────────
phase('Fix')
const fixed = await agent(
  `Apply these accepted review findings to the working tree, coherently and minimally — match surrounding `
  + `code, don't over-refactor, don't introduce new behavior. Then run \`${VERIFY_CMD}\` and iterate until it `
  + `passes. Do NOT commit. Accepted findings:\n${JSON.stringify(triaged.accepted, null, 2)}`,
  { label:'fix:apply', phase:'Fix', model:'sonnet', effort:'high', schema: FIXED },
)
const reverify = await agent(
  `From the repo root run \`${VERIFY_CMD}\` and report pass/fail with any failing test names. Change nothing.`,
  { label:'fix:verify', phase:'Fix', model:'haiku', effort:'low', schema: FIXED },
)
return { findings: triaged, fixed, green: reverify?.verified === true }
```

### Notes that keep it correct

- **Triage is the gate — not the confidence score.** Every lens finding (+ thermo-nuclear) reaches triage by
  default. The Haiku scorer is an *optional* noise-strip for large audits (`SCORE_FLOOR`), never a precision
  gate: a hard floor lets the weakest agent overrule the strongest by deleting real findings before triage
  weighs them. Triage (Opus) verifies each finding against the code and decides real-vs-noise — precision
  belongs there. (This replaced an earlier `THRESHOLD=80` design that demonstrably dropped a real `78`.)
- **Fix is one coherent agent, not a per-finding `parallel()`** — accepted findings often touch the same files,
  and parallel editors would clobber each other. If the accepted set is provably file-disjoint and large, you
  may `pipeline()` it with `isolation:'worktree'` instead; otherwise keep the single applier.
- **Return a structured contract** (`{ findings, fixed, green }`) so the *host* workflow can branch on it —
  e.g. fail the run or skip a commit phase when `green !== true` or unfixed `critical`s remain.
- **`DIFF` is the only real coupling.** Pass it the upstream implement phase's `filesChanged`, or a git range.
  Everything else is self-contained, so the segment drops into any pipeline position.
- **Don't widen the thermo-nuclear phase into a fan-out.** It's one agent on purpose (it invokes the real
  skill). Only code-review fans out.

## Standalone mode (no host workflow)

When there is no Workflow to splice into, emit a **complete** script: the same `meta`/schemas/phases above
wrapped in a Workflow with `phases` declared in `meta`, reviewing `DIFF = 'develop...HEAD'`. Alternatively,
since nested subagents shipped (Claude Code v2.1.172, subagents may spawn subagents up to 5 levels), you may
instead drive it from a single top-level `Agent`-tool orchestrator subagent that spawns the code-review
reviewers itself and invokes the thermo-nuclear skill directly — useful outside an orchestration. Prefer the
Workflow form when the user is already "in a workflow."

## Reference files

- `references/code-review-roster.md` — the lens prompts (`reviewerPrompt`) + the **verbatim** 0–100 confidence
  rubric and false-positive guidance (`scorerPrompt`). Read this to fill in the fan-out. **Required.**
- `references/thermo-nuclear-rubric.md` — a condensed copy of the thermo-nuclear standards, used only as a
  fallback when the real skill isn't installed. The recipe prefers the real Skill call.
