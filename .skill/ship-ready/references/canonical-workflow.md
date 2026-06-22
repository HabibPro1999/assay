# Canonical Workflow (v2)

The single autonomous Workflow ship-ready launches after the grill. **v2 is a rearchitecture** driven by
measured waste on a real run (a 3.7M-token, 2-hour build whose loop re-scanned a clean feature three times).
The redesign is built on six load-bearing decisions, each tied to evidence:

1. **Two clocks, not one loop.** Correctness+completeness *converge fast and must gate*; maintainability/DRY
   is *bottomless and must not gate*. They are split into **Mechanism A** (a blocking convergence loop) and
   **Mechanism B** (one non-blocking advisory polish pass).
2. **No Adapt phase (single-repo).** The `ProjectProfile` is detected at **intake** (the inline agent is
   already reading the repo to grill) and **inlined as config**. A lean per-target Adapt survives only for
   multi-repo targets the inline stage didn't profile.
3. **Delta- and surface-scoped review.** Lap 1 runs the focused fan-out; lap 2+ reviews **only the files the
   last fix changed**, with **only the lenses whose surface those files touch**.
4. **Incremental triage with memory.** A `disposed` cache carries verdicts across passes; only *new* findings
   reach triage. (On the studied run the same false positive was re-found 3× and wrongly accepted on lap 3 —
   memory prevents both.)
5. **Test-backed completeness + a mechanical, N/A-aware gate.** Each EARS AC carries ≥1 tagged assertion;
   "complete" = the AC-tagged tests pass, folded into the gate. The script computes `green`; a command that
   doesn't exist is `not-applicable` (never blocks), an env-blocked tier-0 is `failed` (never silently green).
6. **Reality-anchored lenses.** A lens is only as good as its oracle. Keep the lenses that judge the code
   against *execution semantics*; cut the ones anchored on lagging artifacts (`prior-prs`, `code-comments`),
   re-anchor convention-checking from CLAUDE.md to **the sibling code** and move it to *prevention* in Implement.

> **Frozen mechanism + config.** The orchestrator fills **only the CONFIG block** (PRD path, targets+profiles,
> contracts, caps) and pastes the rest **verbatim**. The loop, the exit predicate, the disposition cache, the
> delta-derivation, and the gate computation are tested mechanism — re-deriving them per run is what produced
> the historical footguns (the `args`-channel crash, the `[].every()` trap, the skipped-vs-N/A gate bug).
> The `review→triage→fix` interior is still **spliced from `workflow-review-phase`**; keep its two validated
> mechanics: thermo-nuclear is a real `Skill` call in one phase-agent, code-review is the script's own
> `parallel()` fan-out (phase-agents can't spawn subagents).

## Model tiers (a prior — reassess per phase × blast-radius)

| Phase | Prior | Why |
|---|---|---|
| Plan · contract/unified | **opus** | Cross-cutting seam decisions; costly to get wrong. |
| Plan · per-target | sonnet | Conform to a frozen contract + local conventions. |
| Research | sonnet (+Context7) | Doc synthesis. |
| Implement | **opus** | Codegen quality is the product; mirrors sibling code, writes AC tests. |
| Review · security / data-integrity / concurrency | **opus** | Subtle, high-blast-radius — only on relevant surfaces, lap-1. |
| Review · bugs / api-contract / git-history | sonnet | Breadth on the change. |
| Triage | **opus** | The gate — decides what changes. Only *new* findings. |
| Fix | sonnet (escalate on repeated criticals) | Implement a precise finding. |
| Gate / re-verify | haiku | Runs commands; the **script** computes green. |
| Polish (thermo + yagni) | sonnet–opus, **once** | Advisory; never loops. |
| Ship-gate | **opus** | Final judgment + structured verdict. |

## The lens roster — reality-anchored, surface-gated

A lens earns its place by **(blast-radius of a miss) × (reliability of its oracle)**, gated to the surfaces
where the miss is possible — not by raw yield. (See `adaptation-layer.md` §4 for the oracle-reliability
ranking and the full rationale for each keep/cut.)

| Bucket | Lenses | When |
|---|---|---|
| **Core** (change-intrinsic) | `bugs`; `api-contract` | always; `api-contract` if `api` surface |
| **Insurance** (surface-gated, lap-1) | `security`, `data-integrity`, `concurrency` | only on auth/money/public · db/migration · txn/async surfaces |
| **Conditional** | `git-history` | only on hunks that **modify pre-existing** code (blame is meaningless on net-new files) |
| **Polish** (advisory, non-gating) | `thermo-nuclear`, `yagni`/`simplify`, `doc-drift` | Mechanism B, once |
| **Cut from the gate** | ~~`prior-prs`~~, ~~`code-comments`~~, ~~`claude-md`~~ | weak/rotting oracle — see below |

Convention-following is handled by **prevention** (Implement mirrors the sibling code; CLAUDE.md is a hint and
**the code wins on conflict**), and doc/comment **drift** is surfaced as an advisory ledger note in Mechanism B
— never as a blocking gate finding.

## Schemas

Reuse `FINDINGS`, `TRIAGE`, `FIXED` verbatim from `workflow-review-phase`. Add:

```js
// A stable signature so a dispositioned finding never re-enters triage (incremental triage).
const DISPOSITION = { type:'object', additionalProperties:false, required:['key','verdict'], properties:{
  key:{type:'string'},                       // `${file}:${normalizedTitle}` — survives across passes
  verdict:{ enum:['accepted','rejected'] },
  reason:{type:['string','null']} } }

// Gate REPORTS raw status; the SCRIPT computes green. `not-applicable` ⇒ the command doesn't exist (never blocks).
const GATE_RESULT = { type:'object', additionalProperties:false, required:['target','gates'], properties:{
  target:{type:'string'},
  gates:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['name','tier','status','detail'], properties:{
      name:{type:'string'}, tier:{enum:[0,1,2]},
      status:{enum:['passed','failed','skipped','not-applicable']},   // skipped = exists-but-env-blocked
      detail:{type:'string'} } } },
  acTests:{ type:['object','null'], additionalProperties:false,        // completeness, folded into the gate
    properties:{ passed:{type:'array',items:{type:'string'}},          // AC ids whose tagged tests pass
      failing:{type:'array',items:{type:'string'}},                    // AC ids whose tests fail
      untestable:{type:'array',items:{type:'string'}} } } } }          // ACs with no machine assertion (ship-gate judges)

const LEDGER = { type:'object', additionalProperties:false, required:['markers'], properties:{
  markers:{ type:'array', items:{ type:'object', additionalProperties:false,
    required:['kind','location','note','rotRisk'], properties:{
      kind:{enum:['ponytail','doc-drift','deferred-finding']},        // shortcut · stale doc/comment · deferred polish
      location:{type:'string'}, note:{type:'string'},
      ceiling:{type:['string','null']}, upgrade:{type:['string','null']}, rotRisk:{type:'boolean'} } } } }

const SHIP_VERDICT = { type:'object', additionalProperties:false,
  required:['status','criteria','gates','perTarget','recommendation'], properties:{
    status:{ enum:['ship','blocked','needs-human'] },
    criteria:{ type:'array', items:{ type:'object', additionalProperties:false,
      required:['id','met','evidence'], properties:{
        id:{type:'string'}, met:{type:'boolean'}, evidence:{type:'string'} } } },
    gates:{ type:'array', items:{ type:'object', additionalProperties:false,
      required:['name','status','detail'], properties:{
        name:{type:'string'}, status:{enum:['passed','failed','skipped','not-applicable']}, detail:{type:'string'} } } },
    perTarget:{ type:'array', items:{ type:'object', additionalProperties:false,
      required:['target','green','residualFindings'], properties:{
        target:{type:'string'}, green:{type:'boolean'}, residualFindings:{type:'array',items:{type:'string'}} } } },
    simplifications:{ type:['array','null'], items:{ type:'object', additionalProperties:false,   // the LEDGER (advisory)
      required:['kind','location','note','rotRisk'], properties:{
        kind:{type:'string'}, location:{type:'string'}, note:{type:'string'},
        ceiling:{type:['string','null']}, upgrade:{type:['string','null']}, rotRisk:{type:'boolean'} } } },
    integration:{ type:['object','null'], additionalProperties:true },
    risk:{ type:['string','null'] }, recommendation:{ type:'string' } } }
```

`simplifications` is **accepted, tracked debt** — it does NOT affect the exit predicate or `status` (a clean
run ships with it listed). It only keeps a deferral from silently becoming permanent.

## The script

```js
export const meta = {
  name: 'ship-ready',
  description: 'Autonomous delivery: plan → research → implement → converge → polish → ship-gate',
  phases: [
    { title: 'Plan' }, { title: 'Research' }, { title: 'Implement' },
    { title: 'Converge' }, { title: 'Polish' }, { title: 'Ship-gate' },
  ],
}

/* ═══════════ CONFIG — the orchestrator fills ONLY this block (from intake). ═══════════
   Everything below it is the FROZEN MECHANISM: paste verbatim. The ProjectProfile is detected at
   INTAKE and inlined here — there is no Adapt phase for single-repo. (Multi-repo: splice a lean
   parallel Adapt before Plan for any target whose profile isn't already inlined.) */
const prdPath = '.prd/<slug>.md'
const targets = [
  { name:'<svc>', repoPath:'/abs/<svc>', surfaces:['api','db'],
    profile:{
      commands:{ typecheck:'…', lint:'…', format:'…', unit:'…', acTests:'…', integration:'…', verify:'…' },
      cmdExists:{ typecheck:true, lint:true, format:false, unit:true, acTests:true, integration:true }, // false ⇒ not-applicable
      conventions:'mirror <sibling modules>; the CODE wins over CLAUDE.md on conflict',
      fileLensMap:[ ['controller', ['api-contract','security']], ['schema', ['data-integrity']],
                    ['migration', ['data-integrity']], ['', ['bugs']] ],          // path-substr → lenses
      buildsClean:true } },
]
const contracts = []                                   // multi-repo seams (Plan derives); [] single-repo
const sequence  = [{ target: targets[0].name, dependsOn: [] }]
const CAP_A  = 4                                        // correctness-convergence backstop (predicate exits first)
const POLISH = 1                                        // maintainability passes — hard cap, NON-blocking

/* ═══════════ FROZEN MECHANISM (paste verbatim) ═══════════ */
const multiRepo = targets.length > 1
const byName = (a, k='target') => Object.fromEntries(a.filter(Boolean).map(x => [x[k], x]))
async function aretry(prompt, opts, tries=3) {        // one transient 529 must not abort a multi-minute build
  let r = null
  for (let i=0;i<tries;i++){ r = await agent(i? `${prompt}\n\n(retry ${i+1}/${tries} after empty result)`:prompt, opts); if (r) return r }
  return r
}
// reality-anchored, surface-gated lens selection
const SURFACE_LENS = { api:['api-contract','security'], db:['data-integrity'], async:['concurrency'],
  infra:['security'], ui:['a11y'] }
function lensesFor(surfaces, opusKeys=new Set(['security','concurrency','data-integrity'])) {
  const base = ['bugs']
  const add = surfaces.flatMap(s => SURFACE_LENS[s] || [])
  return [...new Set([...base, ...add])].map(k => ({ key:k, model: opusKeys.has(k)?'opus':'sonnet' }))
}
function lensesForFiles(changedFiles, profile) {       // delta laps: only lenses whose surface the change touches
  const keys = new Set(['bugs'])
  for (const f of changedFiles) for (const [sub, ls] of profile.fileLensMap) if (sub==='' || f.includes(sub)) ls.forEach(k=>keys.add(k))
  const opus = new Set(['security','concurrency','data-integrity'])
  return [...keys].map(k => ({ key:k, model: opus.has(k)?'opus':'sonnet' }))
}
const dispKey = f => `${f.file}:${(f.title||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().slice(0,80)}`

// ── PLAN ── (multi-repo: contracts+DAG first, then per-target) ──────────────────
phase('Plan')
const plan = await aretry(
  `Read the PRD at ${prdPath}. Produce the implementation plan for ${targets.map(t=>t.name)}. Conform to each `
+ `repo's conventions (mirror the sibling modules named in its profile; the CODE is the convention oracle — `
+ `if CLAUDE.md conflicts with the prevailing code pattern, follow the code and note the doc drift). `
+ (multiRepo ? `Freeze the cross-target contracts ${JSON.stringify(contracts)} and the dependency sequence first. ` : ``)
+ `CRITICAL: map EACH acceptance criterion (AC id) to at least one concrete test assertion to write in Implement; `
+ `where the stack genuinely cannot assert a criterion, mark it untestable (the ship-gate will judge it).`,
  { label:'plan', phase:'Plan', model:'opus', effort:'high', schema: PLAN })

// ── RESEARCH ── current best practices for the libs actually in use ─────────────
phase('Research')
const research = await aretry(
  `Via Context7 (mcp__plugin_context7_context7__*) + web where needed, pull current best practices for the `
+ `libraries this change touches; reconcile with the repo's existing patterns. Concise, actionable.`,
  { label:'research', phase:'Research', model:'sonnet' })

// ── IMPLEMENT ── DAG order; lazy build; mirror sibling code; AC→test; ponytail markers ─
phase('Implement')
await implementInDagOrder(targets, sequence, t => aretry(
  `Implement ${t.name} per the plan ${JSON.stringify(plan)} and research ${JSON.stringify(research)}. `
+ `MIRROR the sibling code named in conventions (${t.profile.conventions}) — the code is the oracle, CLAUDE.md a hint. `
+ `Build LAZY (YAGNI): stdlib → native → installed dep → one line → only then new code; no unrequested abstractions; `
+ `NEVER simplify away validation/error-handling/security/anything the PRD requires. Write ≥1 tagged test per AC `
+ `(name it so the gate can run AC-tagged tests). Mark deliberate shortcuts \`ponytail: <ceiling>, <upgrade>\`. `
+ `Do NOT commit. In a worktree, \`git add -A\` so the diff is real.`,
  { label:`impl:${t.name}`, phase:'Implement', model:'opus', effort:'high',
    isolation: multiRepo?'worktree':undefined, schema: FIXED }))

// ══════════ MECHANISM A — converge correctness + completeness (BLOCKING) ══════════
const disposed = new Map()                              // dispKey → {verdict, reason} — persists across passes
let pass = 0, cursor = null, lastA = null
while (true) {
  pass++; log(`converge pass ${pass}/${CAP_A}`)
  phase('Converge')

  // STAGE + derive the diff to review. Pass 1: whole change. Pass 2+: ONLY what the last fix changed.
  const view = await aretry(
    `In ${targets[0].repoPath}: \`git add -A\`, then return (a) the full staged file list, and (b) the files `
  + (cursor ? `changed SINCE ${cursor} (the last fix).` : `(this is pass 1 — all staged files).`)
  + ` Read-only except the add. Return {changedFiles:[...], head:'<sha>'}.`,
    { label:`stage:${pass}`, phase:'Converge', model:'haiku', effort:'low',
      schema:{type:'object',additionalProperties:false,required:['changedFiles','head'],
        properties:{changedFiles:{type:'array',items:{type:'string'}},head:{type:'string'}}} })
  const changed = (view && view.changedFiles) || []

  // REVIEW — reality-anchored, surface-gated, delta-scoped. Reviewers are told what's already dispositioned.
  const lenses = pass===1 ? lensesFor(targets[0].surfaces) : lensesForFiles(changed, targets[0].profile)
  const skipList = [...disposed.keys()].slice(0, 120)
  const reviewed = await parallel(lenses.map(l => () => agent(
    `Review ${pass===1?'the staged change':'ONLY these changed files: '+JSON.stringify(changed)} in ${targets[0].repoPath} `
  + `through the ${l.key} lens (judge the CODE against execution semantics — not against docs/comments, which rot). `
  + `Do NOT re-report anything matching these already-decided items: ${JSON.stringify(skipList)}. `
  + `Empty findings is a good result; verify framework defaults before asserting (e.g. status codes).`,
    { label:`review:${l.key}:${pass}`, phase:'Converge', model:l.model, effort:l.model==='opus'?'high':'medium', schema: FINDINGS })))
  const fresh = reviewed.filter(Boolean).flatMap(r=>r.findings||[]).filter(f => !disposed.has(dispKey(f)))

  // TRIAGE — only NEW findings. Record every verdict into the disposition cache.
  let accepted = []
  if (fresh.length) {
    const tri = await aretry(
      `Triage these NEW findings against the diff in ${targets[0].repoPath}. Dedupe; drop pre-existing issues, `
    + `nitpicks, false premises (verify the claim against the actual code/framework), and anything a typechecker/`
    + `linter/CI catches. Keep only real, in-diff, worth-changing items. Findings:\n${JSON.stringify(fresh)}`,
      { label:`triage:${pass}`, phase:'Converge', model:'opus', effort:'high', schema: TRIAGE })
    accepted = (tri && tri.accepted) || []
    for (const f of fresh) disposed.set(dispKey(f), {verdict:'rejected'})
    for (const a of accepted) disposed.set(dispKey(a), {verdict:'accepted'})
    if (accepted.length) {
      phase('Converge')
      await aretry(`Apply these accepted findings to ${targets[0].repoPath} coherently and minimally — match `
        + `surrounding code, no new behavior. Then run \`${targets[0].profile.commands.verify}\` until tier-0 passes. Do NOT commit. `
        + `Findings:\n${JSON.stringify(accepted)}`,
        { label:`fix:${pass}`, phase:'Converge', model:'sonnet', effort:'high', schema: FIXED })
    }
  }

  // GATE — mechanical, N/A-aware, completeness folded in (AC-tagged tests). Agent REPORTS; script COMPUTES green.
  const gate = await aretry(
    `From ${targets[0].repoPath}, re-derive the diff (read-only) and run the tiered gates using ${JSON.stringify(targets[0].profile.commands)} `
  + `and existence map ${JSON.stringify(targets[0].profile.cmdExists)}: a command that does NOT exist → status 'not-applicable'; `
  + `a tier-0 command that exists but the env can't run → 'failed' (never 'skipped'); env-blocked tier-1 (e.g. Docker) → 'skipped'. `
  + `ALSO run the AC-tagged tests and report, per AC id, passed / failing / untestable. Change nothing.`,
    { label:`gate:${pass}`, phase:'Converge', model:'haiku', effort:'low', schema: GATE_RESULT })

  // HARNESS-OWNED EXIT — fail-safe (positive evidence required; null reads as NOT clean).
  const gs = (gate && gate.gates) || []
  const tier0Ran = gs.some(g => g.tier===0 && g.status==='passed')
  const gatesGreen = tier0Ran && gs.every(g => g.status==='passed' || g.status==='not-applicable' || (g.status==='skipped' && g.tier!==0))
  const ac = gate && gate.acTests
  const complete = !!ac && (ac.failing||[]).length===0       // untestable ACs defer to the ship-gate, don't block here
  const clean = accepted.length===0 && gatesGreen && complete
  lastA = { pass, gate, accepted: accepted.map(a=>a.title), disposed: disposed.size }
  cursor = (view && view.head) || cursor
  if (clean) { log('converged — correctness + completeness green'); break }
  if (pass >= CAP_A) { log('hit convergence cap with residuals — verdict will be blocked'); break }
  // else: next pass reviews ONLY the fix delta with surface-relevant lenses.
}

// ══════════ MECHANISM B — polish ONCE (NON-blocking, advisory) ══════════
phase('Polish')
let ledger = { markers: [] }
for (let i=0;i<POLISH;i++){
  const q = await aretry(
    `Invoke Skill({ skill:'thermo-nuclear-code-quality-review' }) and apply the \`yagni\` lens to the FULL diff in `
  + `${targets[0].repoPath}: find over-engineering/duplication to DELETE (delete/stdlib/native/yagni/shrink; net −lines). `
  + `Also flag DOC-DRIFT: any CLAUDE.md rule or code comment the implementation now contradicts (the code is right — the doc is stale). `
  + `Return findings.`,
    { label:'polish:review', phase:'Polish', model:'opus', effort:'high', schema: FINDINGS })
  const qa = await aretry(`Triage ${JSON.stringify((q&&q.findings)||[])}: accept only cheap, clearly-worth-it cleanups (obvious DRY extractions). Everything else is deferred, not rejected.`,
    { label:'polish:triage', phase:'Polish', model:'sonnet', effort:'medium', schema: TRIAGE })
  const acc = (qa&&qa.accepted)||[]
  if (acc.length) await aretry(`Apply these cheap cleanups to ${targets[0].repoPath}, then run \`${targets[0].profile.commands.verify}\` (must stay tier-0 green). Do NOT commit. ${JSON.stringify(acc)}`,
    { label:'polish:fix', phase:'Polish', model:'sonnet', effort:'medium', schema: FIXED })
  const harvested = await aretry(
    `In ${targets[0].repoPath}, grep for \`(#|//|--) ?ponytail:\` markers (skip node_modules/.git/build). Each → a ledger row `
  + `(kind:'ponytail', location, note, ceiling, upgrade; rotRisk=true if no upgrade trigger). Add the deferred polish findings `
  + `(kind:'deferred-finding') and the doc-drift items (kind:'doc-drift') from this evidence: ${JSON.stringify((qa&&qa.rejected)||[])}.`,
    { label:'polish:ledger', phase:'Polish', model:'haiku', effort:'low', schema: LEDGER })
  if (harvested && harvested.markers) ledger = harvested
}

// ══════════ SHIP-GATE — structured verdict (explains; cannot invent green) ══════════
phase('Ship-gate')
const verdict = await aretry(
  `You are the ship-readiness gate. Read the PRD at ${prdPath} and decide from the evidence. status='ship' ONLY if every AC `
+ `is met (AC-tagged tests pass; judge 'untestable' ACs against the diff), all tier-0 gates are green (N/A and env-skipped `
+ `tier-1 are fine), and no unresolved critical/high finding remains. Set \`simplifications\` to the harvested ledger VERBATIM — `
+ `accepted, tracked debt, NOT a reason to block; a clean run ships WITH it listed; raise \`risk\` for any rotRisk entry. `
+ `status='blocked' if residuals remain after the convergence cap; 'needs-human' if a criterion is contradictory. `
+ `Evidence:\n${JSON.stringify({ converge: lastA, ledger })}`,
  { label:'ship-gate', phase:'Ship-gate', model:'opus', effort:'high', schema: SHIP_VERDICT })
return verdict || { status:'blocked', criteria:[], gates:[], perTarget:[{target:targets[0].name,green:false,residualFindings:['ship-gate returned no result']}], recommendation:'Re-run the ship-gate.' }
```

## Helpers the orchestrator pastes (part of the frozen mechanism)

- `implementInDagOrder(targets, sequence, fn)` — run targets with no unmet deps via `parallel()`, then the next
  wave. One target / empty DAG ⇒ a `parallel()` of one.
- The disposition cache (`disposed`), the delta cursor (`cursor`), and `lensesFor*` are the v2 mechanism — they
  are why review cost shrinks each pass and triage stops re-litigating ghosts. Do not "simplify" them away.

## Authoring rules (v2)

- **Fill only the CONFIG block; paste the mechanism verbatim.** This is what makes the loop/predicate/cache
  reliable and kills the historical footgun class. Don't read from `args`.
- **Every `phase:` string ∈ `meta.phases`.** The whole convergence loop uses `phase('Converge')`; polish uses
  `phase('Polish')`. One label set, used everywhere.
- **The exit is the script's job, fail-safe.** `clean` needs positive evidence (tier-0 actually `passed`,
  AC tests not failing, `accepted===0`); a null/empty result reads as NOT clean. Remember `[].every()` is `true`,
  so pair every "all passed" with a "tier-0 actually ran" check.
- **Completeness is the AC-tagged tests, not a separate opus pass.** Where a criterion is genuinely untestable,
  it defers to the ship-gate (flagged), it does not silently pass.
- **Polish never gates and never loops past `POLISH`.** It applies cheap wins and writes the ledger; everything
  else is advisory. `needs-human` from the ship-gate resumes (`resumeFromRunId`), it doesn't restart.

## Why the exit is the script's job

A model deciding "are we done?" calls a 90%-done change shipped. The harness computes `clean` from objective
signals — `accepted===0`, tier-0 `passed`, AC tests not failing — so the loop can't terminate on vibes, and the
ship-gate *explains* the verdict without getting to *invent* a green one. v2 keeps that and adds: the loop can't
**waste** either — it reviews only the delta, triages only what's new, and stops the bottomless quality axis from
holding the cheap correctness axis hostage.
