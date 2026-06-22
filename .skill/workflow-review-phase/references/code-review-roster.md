# Code-Review Roster (diff-scoped fan-out)

This reproduces the official `/code-review` engine as a workflow-native fan-out, adapted to review a **diff**
(not a GitHub PR) so it composes inside a Workflow. Each lens is an independent reviewer agent; every finding
it returns goes to **triage** (the gate). Optionally — for large audits only — findings can first be scored
0–100 so near-certain false positives are stripped before triage (see `SCORE_FLOOR`); by default nothing is
dropped pre-triage.

Two things are faithful to the original and must stay verbatim: the **0–100 confidence rubric** and the
**false-positive guidance**. The reviewer roster keeps the original 5 lenses and adds `security` + `concurrency`.

## `reviewerPrompt(lensKey, DIFF)`

Each lens reviews only the change set (`DIFF`) and returns findings per the `FINDINGS` schema — each with a
clear `title`, `file`, `line` (or null), `severity`, `category` (set to the lens key), and a one-paragraph
`rationale`. Tell every reviewer: focus on the change itself, prefer real issues over nitpicks, and ignore
anything a typechecker/linter/compiler/CI would catch.

| `lensKey` | Reviewer prompt (fill in `${DIFF}`) | Default model |
|---|---|---|
| `claude-md` | "Audit the changes in `${DIFF}` against the repository's CLAUDE.md guideline files (root + any in modified dirs). CLAUDE.md is guidance for writing code, so not every line applies during review — only flag a violation when the CLAUDE.md actually calls out that specific thing. Return findings." | sonnet |
| `bugs` | "Read the file changes in `${DIFF}` and do a shallow scan for **obvious, large** bugs in the changes themselves. Stay within the change set; don't go spelunking for extra context. Focus on real functional bugs; skip nitpicks and likely false positives." | sonnet |
| `git-history` | "Read the git blame/history of the code modified in `${DIFF}`. Flag bugs that are only visible in light of that history — e.g. a change that reintroduces a previously-fixed bug, breaks an invariant a past commit established, or contradicts the reason a line was written." | sonnet |
| `prior-prs` | "Find prior pull requests / commits that touched the files in `${DIFF}` and read any review comments on them. Flag issues where guidance from those past reviews also applies to this change." | sonnet |
| `code-comments` | "Read the code comments in and around the files modified in `${DIFF}`. Ensure the changes comply with any guidance, invariant, or warning those comments express; flag where the change violates a documented assumption." | sonnet |
| `security` | "Security review of `${DIFF}` only. Look for: missing authz/ownership checks, broken authentication, injection (SQL/command/path), secrets or tokens in code/logs, unsafe deserialization, SSRF, missing input validation on a trust boundary, and data exposure in responses. Flag concrete, in-diff issues with the exploit path in the rationale." | **opus** |
| `concurrency` | "Concurrency & data-integrity review of `${DIFF}` only. Look for: races, lost updates, TOCTOU, missing/incorrect locking or lock-ordering, non-atomic read-modify-write, idempotency gaps, retry/at-least-once hazards, and transaction-boundary mistakes. Reason explicitly about interleavings; flag the specific sequence that breaks." | **opus** |

> If the codebase isn't one where a lens applies (e.g. no auth surface in the diff), that lens should return
> an empty `findings` array rather than inventing something. Empty is a valid, good result.

## `scorerPrompt(finding, DIFF)` — verbatim confidence rubric

For each finding, score 0–100 for how confident you are it is a **real** issue (vs a false positive). For a
finding flagged on CLAUDE.md grounds, first double-check the CLAUDE.md actually calls out that issue
specifically. Give the agent this scale **verbatim**:

- **0 — Not confident at all.** A false positive that doesn't stand up to light scrutiny, or a pre-existing issue.
- **25 — Somewhat confident.** Might be real, might be a false positive; couldn't verify. If stylistic, it was
  not explicitly called out in the relevant CLAUDE.md.
- **50 — Moderately confident.** Verified it's a real issue, but it might be a nitpick or rare in practice;
  relative to the rest of the change, not very important.
- **75 — Highly confident.** Double-checked and very likely a real issue that will be hit in practice; the
  current approach is insufficient. Important and will directly impact functionality, or directly named in the
  relevant CLAUDE.md.
- **100 — Absolutely certain.** Double-checked and confirmed it is definitely a real issue that will happen
  frequently in practice; the evidence directly confirms it.

Return `{ confidence: <0-100>, verdict: <one line> }`. This scorer runs **only when `SCORE_FLOOR` is set**
(large audits). Then drop findings with `confidence < SCORE_FLOOR` (~25 — near-certain false positives only)
and pass `confidence` to triage as a signal. By default scoring is skipped entirely and triage is the sole gate.

## False positives to discard (verbatim guidance)

Tell both the reviewers and the scorers to treat these as non-issues:

- Pre-existing issues (not introduced by this change).
- Something that looks like a bug but is not actually a bug.
- Pedantic nitpicks a senior engineer wouldn't call out.
- Issues a linter, typechecker, or compiler would catch (missing imports, type errors, broken tests,
  formatting, pedantic style). Assume CI runs these separately.
- General code-quality gripes (test coverage, documentation, vague "security" hand-waving) **unless** the
  relevant CLAUDE.md explicitly requires it. (Note: the dedicated `security`/`concurrency` lenses DO surface
  concrete, in-diff security/race bugs — that's different from a generic "add more tests" nit.)
- Issues that CLAUDE.md mentions but the code explicitly silences (e.g. a lint-ignore comment).

## Scaling

- **Small diff / quick check:** drop to `['bugs','claude-md','security']`.
- **Full audit:** keep all 7; consider running two independent `bugs` reviewers and taking the union (the
  original `/code-review` runs the CLAUDE.md lens twice for redundancy — do the same for `bugs` on big diffs).
- **Precision is triage's job, not a threshold.** Leave `SCORE_FLOOR` off and let triage cut — it's the
  smartest agent and verifies against the code. Enable a low `SCORE_FLOOR` (~25) only when candidate volume on a
  big audit would overwhelm a single triage agent; raise it no higher, or you start deleting real findings.
