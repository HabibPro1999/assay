# ship-ready — multi-angle review

*An ultracode review from five angles, ground-truthed against the official Claude Code docs and the mid-2026 spec-driven-development market. 25 review agents; high-impact findings adversarially verified (14/16 stood); the load-bearing "is Workflow real?" question re-verified against `code.claude.com/docs` after the first ground-truth agent failed.*

---

## Verdict

ship-ready is a **strong, genuinely differentiated skill** built on one defensible idea that no competitor packages together: a **script-decided** (not model-decided) convergence gate that splits **correctness** (blocks ship) from **cleanliness** (advisory only). The SKILL.md authoring is essentially exemplary against Anthropic's published rules. Two real risks keep it from being merge-ready *as a distributable*:

1. **An undisclosed runtime floor.** The whole autonomous stage is a Claude Code **Workflow** — which *is* GA, but requires **Claude Code v2.1.154+** and a **paid plan**. The skill states no version/plan requirement and ships no fallback, so for a user below that floor it silently won't run.
2. **The canonical script is not paste-runnable.** A frozen-mechanism helper it tells you to "paste verbatim" (`implementInDagOrder`) has no body, and the convergence loop is hardwired to `targets[0]` — so the multi-repo machinery the docs describe at length is absent from the actual script.

Everything else is polish. The methodology is sound; the cost model is the thing most users will feel.

---

## What it gets right

- **The two-clocks insight is correct and rare.** Splitting "are we done?" into Mechanism A (correctness/completeness that *converges and gates*, `canonical-workflow.md:207-275`) and Mechanism B (maintainability that is *bottomless and never gates*, `:277-298`) is the right answer to its own documented failure mode — a 3.7M-token run whose loop re-scanned clean code three times. Refusing to let a copy-pasted helper hold the machine for another expensive lap is a specific, correct call.
- **The exit predicate is genuinely fail-safe.** `canonical-workflow.md:265-269` guards the classic `[].every() === true` trap with an explicit `tier0Ran = gs.some(g => g.tier===0 && g.status==='passed')`, treats a null gate/AC read as *not* clean, and requires positive evidence to go green. This is the detail naive "loop until clean" agents get wrong.
- **Delta-scoped review with finding-memory.** The `disposed` Map (`:208`, `:233`, `:244-245`) keeps dispositioned findings out of triage forever; pass 2+ reviews only the files the last fix changed (`lensesForFiles`, `:169-174`) with only the lenses those files' surfaces touch. Real, measured cost control — not hand-waving.
- **Reality-anchored lens epistemics.** "A lens is only as good as its oracle" (`adaptation-layer.md:142-148`) — keep execution-anchored lenses (`bugs`/`security`/`data-integrity`/`concurrency`), demote artifact-anchored ones (`prior-prs`/`code-comments`/`claude-md`) that false-flag correct code contradicting a stale doc — is more honest review epistemics than any competitor states.
- **Spec-compliant authoring.** `name` `ship-ready` (10 chars, matches dir), description **875 chars** (under the 1024 cap), third-person, what+when, SKILL.md **204 lines** (under 500), progressive disclosure via `references/`, `disable-model-invocation: true` used correctly. The one-line companions (`grill-me`, `grilling`) are valid. *(All confirmed against `platform.claude.com/docs/.../agent-skills/best-practices` and `code.claude.com/docs/en/skills`.)*
- **Clean single-target collapse.** `multi-repo-contracts.md:92-102` — one node, no contracts, empty DAG, fan-outs become `parallel()` of one. *Intent* is to handle "add a button" and a three-service feature with one code path (but see H2 — the script doesn't yet implement the multi-repo half).

---

## Against the Claude Code docs

| Claim in ship-ready | Verdict | Notes |
|---|---|---|
| name / description-length / third-person / 500-line rules | **confirmed** | Measured; all pass. |
| name matches directory | **confirmed** | `ship-ready`, `grill-me`, `grilling` all match. |
| Progressive disclosure via `references/` | **confirmed** | SKILL.md is an overview; depth in four files, each described. |
| `disable-model-invocation: true` is valid, user-only | **confirmed** | Documented in `code.claude.com/docs/en/skills`; also moots the listing-truncation concern (description never sits in startup context). |
| References kept one level deep | **partly** | SKILL.md links all four directly (good), but `intake-and-spec.md` and `multi-repo-contracts.md` cross-link siblings — the second-level chains the docs warn against. |
| **The "Workflow" runtime exists and is usable** | **confirmed — with a floor the skill hides** | Workflows are documented (`code.claude.com/docs/en/workflows`), GA on **paid plans**, requiring **Claude Code v2.1.154+**, with `agent()`/`parallel()`/`pipeline()`/`phase()` primitives. ship-ready's "author a Workflow per run" model matches how they actually work. **But the skill states no version/plan requirement and no degraded fallback** — below the floor it silently fails. |
| **Phase-agent CANNOT spawn subagents** (the rationale for the script-level `parallel()` fan-out) | **undocumented + undercut** | No official doc states this restriction — it's an undocumented runtime detail the architecture leans on. And nested subagents **shipped** (changelog **v2.1.172**, ~June 2026: subagents spawn subagents, **5-level** limit), which `workflow-review-phase/SKILL.md:181` itself admits — so the constraint that justifies the split is, by the bundle's own words, no longer absolute. |
| `resumeFromRunId` resume semantics | **partly** | Real, but an **Agent SDK** parameter (`WorkflowInput`), not a CLI user feature. The skill's `needs-human` resume story works through it but inherits the SDK-level caveat. |
| Skills auto-discovered as laid out | **refuted (install gap)** | They live under `.skill/`, not `.claude/skills/`. They're a *portable bundle* — the README's `cp -R .skill/* ~/.claude/skills/` is the (correct) install step, but the model can't load them from `.skill/` in place. |

---

## Against the market

The category went mainstream in 2026 and is crowded. ship-ready's pitch ("approved spec → long-running autonomous build → ship") is **near-identical to cc-sdd's** — so the differentiator has to be legible, and it's subtle.

| Competitor | Overlap | Where ship-ready differs / leads | Reinventing? |
|---|---|---|---|
| **GitHub Spec Kit** (~93K★, agent-agnostic SDD CLI) | Front half: EARS spec before code | Spec Kit stops at handing tasks to an agent — no convergence loop, no mechanical gate, no AC→test enforcement | **Partly** — EARS + spec-before-code are now Spec-Kit-standard; ship-ready re-implements them inside its grill instead of interoperating with `spec.md`/`tasks.md` |
| **AWS Kiro** (closed IDE, native SDD) | Closest conceptual twin: requirements→design→autonomous TDD + reviewer + auto-debug | Kiro's reviewer is **model-driven**; ship-ready's gate is **script-decided**. Kiro bundles `design.md` (a HOW doc ship-ready omits). Kiro doesn't split correctness-gating from cleanliness-advice | Conceptual overlap, different gate epistemics |
| **cc-sdd** (multi-agent Claude Code SDD harness) | **Most direct competitor** — same one-liner, "code is source of truth", human-approves-at-gates | ship-ready adds the grill-to-zero-ambiguity intake, script-decided convergence + finding-memory, two-clocks split. **But cc-sdd is multi-agent-portable; ship-ready is Workflow-locked** | Overlap near-total on intent; differentiation is the back end |
| **BMAD-METHOD** (~49K★, 12-persona agile) | PRD-first, phased planning | ship-ready collapses personas into one orchestrator + a mechanical gate; far more rigorous about "done" | No — different shape |
| **Taskmaster** | PRD-parse-to-tasks slice | Complementary — Taskmaster owns WHAT-next; ship-ready owns intake→build→gate→ship and decides DONE | No — could feed ship-ready |
| **Matt Pocock's skills** (~135K★, small + composable) | `to-prd` ~ intake; `tdd`/`diagnosing-bugs` folded into Implement | Writes a *product* PRD (pure WHAT); encodes tdd/diagnosing inline. **Philosophical tension: Pocock wins on SMALL + composable; ship-ready is one large opinionated orchestrator** | No, but heavier — adoption friction vs the aesthetic it credits |
| **obra/superpowers** (~170K★, end-to-end framework) | brainstorming ~ grill; two-stage review ~ the split; verification-before-completion ~ the gate; YAGNI | superpowers' review is **model-judged with human checkpoints**; ship-ready makes loop-again/stop **script-mechanical**, adds finding-memory + delta-scoping + a hard AC→test oracle. Broader/more portable vs narrower/more deterministic | No — meaningfully more deterministic back end |
| **Anthropic Agent SDK + `/code-review`** | The substrate, not a rival | ship-ready's value is opinionated assembly on top. **Dependency risk**: Anthropic could ship a first-party spec→build→gate flow; Workflow lock-in makes it non-portable. It also *reproduces* `/code-review` (`code-review-roster.md`) rather than calling it — duplicate surface that will drift | Partial — reproduces the review engine |
| **Devin / Factory / Cursor** (commercial autonomous) | Outcome (ticket in → tested PR out), multi-repo long-horizon | Edge is methodological transparency (inspectable, script-decided gate) vs opaque judgment. **But they own the Jira/Linear/Slack/CI integrations ship-ready only detects, and can absorb its rigor** | No integration moat |

**Net:** competitors standardize the **front** (spec/EARS/tasks) or the **autonomy** (Devin/Factory). ship-ready's unique, defensible contribution is a rigorous, cheap, **mechanically-decided back end** — a correctness gate that converges and a cleanliness clock that advises. The danger is that this is hard to convey in a star-driven market, so it risks being lumped in with the dozens of `requirements→design→tasks` harnesses despite being more rigorous.

---

## Findings by severity (verified)

### Critical

**C1 — Stage-2 depends on a Workflow runtime floor the skill never discloses.** *(practical-adoption)*
The autonomous stage is a Workflow (`canonical-workflow.md:124-311`). Workflows are GA — but require **Claude Code v2.1.154+** and a **paid plan**, and `resumeFromRunId` is an Agent-SDK-level parameter. The skill states **no version requirement, no plan caveat, and no degraded single-agent fallback**, and installs to a non-standard path (`.skill/`, not `.claude/skills/`) with hard Context7 + `/code-review` deps. Below the floor it fails with no signal why.
**Fix:** add an explicit "Requires Claude Code ≥ 2.1.154, paid plan; Workflow tool" line + the `.skill/` → `.claude/skills/` install note to SKILL.md/README; document a degraded fallback. Reconcile the phase-agent-nesting rationale with the v2.1.172 nested-subagent reality (pick the post-2.1.172 truth).

### High

**H1 — `implementInDagOrder` is "paste verbatim" but has no body.** *(script-correctness — verified, conf 0.93)*
Called at `:197` inside the "FROZEN MECHANISM (paste verbatim)" block (`:153`) and listed at `:315-316` as a pasted helper — yet only an English description exists. Every *other* pasted helper (`byName:155`, `aretry:156`, `lensesFor:164`, `lensesForFiles:169`, `dispKey:175`) has a real JS body. This directly violates the doc's thesis that re-deriving mechanism per run *is* the footgun class v2 eliminated.
**Fix:** add the actual `async function implementInDagOrder(targets, sequence, fn)` body (wave computation over `sequence.dependsOn`, `await parallel()` per wave) to the frozen block.

**H2 — The convergence loop is hardwired to `targets[0]`; the multi-repo machinery is absent from the script.** *(script-correctness — verified, stands)*
Mechanism A, the gate, and polish all reference `targets[0]` only (`:218`, `:228`, `:257`, `:284`). There is no integration lens, no per-target convergence, no cross-target gate — all heavily documented in `multi-repo-contracts.md`. The "same script handles three services" claim is not yet true in the pasted mechanism.
**Fix:** either implement the multi-repo loop or scope the skill's claims to single-repo until it exists.

**H3 — Completeness == "AC-tagged tests pass" has no test-quality oracle.** *(methodology — verified, stands)*
`clean` requires `(ac.failing||[]).length===0` (`:267-268`), but the **same agent writes both the AC and its test** — a tautological `@AC` assertion yields a green that means nothing, and "untestable ACs defer, flagged" (`:268`) is an escape hatch for exactly the UI/visual/a11y/infra surfaces hardest to test. The gate's headline guarantee is forgeable.
**Fix:** add a triage/ship-gate check that each `@AC` test actually exercises its criterion; surface the `untestable` AC ratio as a `risk` on the verdict.

**H4 — "Kill ALL ambiguity up front" has no path for ambiguity discovered mid-build.** *(methodology — verified, stands)*
The autonomy guarantee rests on the grill killing every ambiguity before the Workflow starts — because a phase-agent can't pause to ask. But discoveries *during* implementation (a contract that can't hold, a missing dependency the preflight missed) have nowhere to go but a heuristic guess or a `needs-human` exit. The enabler is also a structural dead-end.
**Fix:** define the mid-build ambiguity protocol explicitly (when to guess-and-flag vs. exit `needs-human`), and lean on `preflightWarnings`/`buildsClean` to shrink the surface.

**H5 — Two documented lens-key inconsistencies will mislead an implementer.** *(internal-consistency — verified, stands)*
(a) `SURFACE_LENS` uses `infra:['security']`, `ui:['a11y']` (`:162`), while `adaptation-layer.md:159` names them `infra-safety` and `a11y`+`visual/state` — the code never emits `infra-safety`/`visual/state`. (b) `adaptation-layer.md:116` still says conventions "feed … the `claude-md` review lens" — four sections before §4 explicitly **cuts** `claude-md` from the gate, contradicting the load-bearing "convention-following moves to prevention" decision.
**Fix:** pick one canonical key set across code + `adaptation-layer.md` §4 + README; update `:116` to "feed the implement phase (prevention); doc-drift surfaces in Mechanism B."

### Medium

- **M1 — Emitted lens keys have no roster prompt.** `api-contract`/`data-integrity`/`a11y` are emitted by the selectors but `code-review-roster.md` defines prompts only for the original 7. Not a crash (Mechanism A uses an inline prompt), but those lenses run with a bare adjective and none of the roster's verbatim guidance — especially `data-integrity`, treated as a high-blast opus lens.
- **M2 — The "spliced from `workflow-review-phase`" claim is half-true, and that skill's default `LENSES` ship the cut lenses.** Mechanism A uses an inline prompt (`:227-232`), never `reviewerPrompt()`; and `workflow-review-phase/SKILL.md:99-102` defaults `LENSES` to include `claude-md`/`prior-prs`/`code-comments` — exactly the three ship-ready's guardrails cut. A verbatim splice re-introduces them.
- **M3 — Omitted optional `acTests` can force `blocked` on a clean build.** If `acTests` isn't reported, `complete` is false and a passing build can't go green. Confirm a no-AC-tests project degrades gracefully.
- **M4 — No user-facing cost framing.** Documented baseline is 3.7M tokens / 2 hours with an Opus-heavy tier table (`:35-47`) and no cheap-mode — high enough to warrant an expectations note + an optional cheaper tier for small tasks.
- **M5 — README duplicates the guardrails block** (prose `:50-73` + bullets `:152-157`) — redundant context in the user-facing entry doc.
- **M6 — Reality-anchored lens demotion is defensible but contestable.** Teams that keep CLAUDE.md authoritative or rely on PR conventions may see "convention-following by prevention (mirror sibling code)" as weaker than an enforced gate.

### Overturned / false alarms (so you can trust the rest)

- **"`while(true)` converge loop is unsafe under `resumeFromRunId`" — OVERTURNED.** The low-level observations are accurate (loop state is in-memory; per-pass `agent()` count is data-dependent), but the thesis misreads the docs: ship-ready does **not** claim loop-mid-flight resume — `SKILL.md:152` and `canonical-workflow.md:332` scope `needs-human` resume to the **ship-gate**, not a rehydrated convergence Map. No correctness bug.
- **A second false positive in the same area was dropped by adversarial verification.** (14 of 16 high-impact findings stood; 2 were overturned.)

---

## Recommendations (prioritized)

1. **Resolve the runtime-floor disclosure (C1) first.** Add "Requires Claude Code ≥ 2.1.154 + paid plan; uses the Workflow tool" and the `.skill/` → `.claude/skills/` step to SKILL.md/README; document a degraded fallback; and reconcile the phase-agent-nesting rationale against the v2.1.172 nested-subagent reality. Every other strength is moot for a user who can't run Stage 2.
2. **Make the canonical script paste-runnable (H1, H2):** add the `implementInDagOrder` body, and either implement the multi-repo loop or scope the claims to single-repo. This is the largest gap between "verbatim mechanism" and reality.
3. **Close the test-quality hole (H3):** the gate's headline guarantee is currently forgeable by the same agent that writes the tests. Add a tautology/coverage sanity check and surface the `untestable` ratio as risk.
4. **Define the mid-build ambiguity protocol (H4).**
5. **Unify lens-key naming + roster coverage (H5, M1, M2):** one canonical key set; add roster rows for `api-contract`/`data-integrity`/`a11y`; align `workflow-review-phase`'s default `LENSES` with the reality-anchored set (or mark Mechanism A inline-by-design).
6. **Position on the back-end differentiator, loudly (market):** the moat is "script-decided gate + two clocks," not "another SDD harness." Consider interoperating with `spec.md`/`requirements.md` so it drops into existing Spec-Kit/Kiro repos instead of reinventing the front half. Add cost framing + a cheap tier (M4) to blunt the heavyweight-vs-minimal friction.
7. **Tidy docs:** flatten second-level reference cross-links; de-duplicate the README guardrails (M5).

---

*Caveats: the market figures and a few doc URLs were gathered by web-searching agents and reflect mid-2026 sources; treat star counts and version numbers as approximate. The Claude Code mechanics (Workflow GA + version floor, nested-subagent 5-level limit, `disable-model-invocation`, skill-authoring rules) were verified against `code.claude.com/docs` and `platform.claude.com/docs`.*
