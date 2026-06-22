# Thermo-Nuclear Rubric (fallback)

The recipe prefers a **real `Skill({ skill: 'thermo-nuclear-code-quality-review' })` call** — a workflow
phase-agent can invoke it, and it stays in sync with the canonical skill. Use this condensed copy **only** if
that skill isn't installed in the environment.

This is an unusually strict review of **implementation quality, maintainability, and abstraction quality**.
Be ambitious about structure — don't stop at local cleanups; hunt for "code judo": behavior-preserving
restructurings that make the implementation dramatically simpler, smaller, and more direct.

## Baseline prompt

> Perform a deep code quality audit of the diff. Rethink how to structure/implement the changes to meaningfully
> improve code quality without impacting behavior. Improve abstractions and modularity, reduce spaghetti,
> improve succinctness and legibility. Be ambitious — if there's a clear path to a better implementation that
> involves restructuring, go for it. Be extremely thorough and rigorous. Measure twice, cut once.

## Standards (flag against these)

0. **Be ambitious about structural simplification.** Look for reframings where whole branches, helpers, modes,
   conditionals, or layers disappear. Prefer the solution that makes the code feel inevitable in hindsight.
   Prefer deleting complexity over rearranging it.
1. **1k-line file smell.** Don't let a change push a file from under ~1000 lines to over without a strong
   reason; prefer extracting helpers/modules. Flag the threshold crossing and ask whether to decompose first.
2. **No random spaghetti growth.** Be suspicious of new ad-hoc conditionals, scattered special cases, or
   one-off branches dropped into unrelated flows. Push the logic into a dedicated abstraction/helper/state
   machine/policy/module instead of tangling an existing path. Treat "weird if statements in random places" as
   a design problem, not a nit.
3. **Clean the design, don't just accept working code.** If behavior can stay the same while structure gets
   meaningfully cleaner, push for the cleaner version. Prefer removing moving pieces over spreading complexity.
4. **Boring & direct over clever/magic.** Treat brittle, ad-hoc, or "magic" behavior as a quality problem. Be
   skeptical of generic mechanisms hiding simple data-shape assumptions. Flag thin abstractions, identity
   wrappers, and pass-through helpers that add indirection without clarity.
5. **Type & boundary cleanliness.** Question unnecessary optionality, `unknown`/`any`, or cast-heavy code when
   a clearer type boundary exists. Prefer explicit typed models / shared contracts over loosely-shaped ad-hoc
   objects. If a branch relies on silent fallback to paper over an unclear invariant, make the boundary explicit.
6. **Keep logic in the canonical layer and reuse existing helpers** rather than re-deriving it locally.
7. **Parallelize independent work** when that also simplifies the orchestration (and flag needlessly
   serialized independent steps).

## Output

Return findings per the `FINDINGS` schema. Set `severity` by how much the issue hurts long-term codebase
health, and prefer findings whose `suggestedFix` *removes* complexity. This rubric is about maintainability and
structure — pair it with the code-review roster (which owns correctness/security/concurrency bugs).
