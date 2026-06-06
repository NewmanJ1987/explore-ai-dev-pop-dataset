# /verify-pr

Runs a two-phase assumption analysis on a pull request.

**Usage:** `/verify-pr <PR_NUMBER> <COMMIT_SHA>`

---

## Phase 1 — Assumption Extraction

**Scope is strictly limited to:**
- The PR title and description (`gh pr view $PR_NUMBER --json title,body`)
- The PR diff (`gh pr diff $PR_NUMBER`)
- The commit message and patch (`git show $COMMIT_SHA`)

**Do not** read PR comments, review threads, linked issues, commit history beyond `$COMMIT_SHA`, or any files in the codebase. Do not fetch additional context to fill gaps — if the description is vague or incomplete, reflect that in the assumptions. Work only with what is explicitly in the PR description and diff.

1. Fetch the PR title and description using `gh pr view $PR_NUMBER --json title,body`
2. Fetch the PR diff using `gh pr diff $PR_NUMBER`
3. Fetch the commit details using `git show $COMMIT_SHA`
4. Run this analysis against only the above:

   > Read the PR description and see what it claims to do. Assume it may be
   > incorrect — enumerate the assumptions that must hold for this patch to be
   > correct. Take a look at the behavior of existing functions it calls, the
   > state it expects, the control flow it modifies, and the relationship between
   > the change and the stated issue. For each assumption, specify what evidence
   > in the codebase would confirm or refute it.

4. Write the output to `analysis/pr-$PR_NUMBER-assumptions.md` in this format:

```
# Assumptions: PR #<PR_NUMBER> — <PR title>

## Assumption 1: <short label>
**Claim:** <what must be true for the patch to be correct>
**Where to look:** <specific files, functions, or test locations that would confirm or refute this>

## Assumption 2: ...
```

---

## Phase 2 — Assumption Verification (subagent)

Spawn a subagent using Task() with the following instructions. Pass it the PR number and the path to the assumptions file.

**Subagent instructions:**

You are verifying assumptions about a pull request. You have a strict scope — do not explore the full repository.

**Allowed scope only:**
- Files changed in the PR (get the list with `gh pr diff $PR_NUMBER --name-only`)
- Direct imports / dependencies of those changed files (one level deep only — do not follow transitive dependencies)
- Test files that directly test the changed files

**For each assumption in `analysis/pr-$PR_NUMBER-assumptions.md`:**

1. Identify which changed file(s) and their direct dependencies are relevant to this assumption
2. Read only those files
3. Check if any tests directly cover the relevant behavior
4. Classify the assumption as one of:
   - ✅ **Confirmed** — the code or tests provide clear evidence the assumption holds
   - ❌ **Refuted** — the code or tests contradict the assumption
   - ❓ **Unverifiable** — the changed files and their immediate dependencies do not contain enough information; do not speculate or explore further

**Do not** chase transitive dependencies, search the broader codebase, or mark an assumption Confirmed/Refuted based on inference alone. If the evidence isn't in scope, it's Unverifiable.

Write the verdict to `analysis/pr-$PR_NUMBER-verdict.md` in this format:

```
# Verification Verdict: PR #<PR_NUMBER>

## Assumption 1: <label>
**Verdict:** ✅ Confirmed / ❌ Refuted / ❓ Unverifiable
**Evidence:** <specific file + line or test that supports the verdict, or a one-line explanation of why it's unverifiable>

## Assumption 2: ...

---
## Summary
<2–3 sentences: overall confidence in the patch, any refuted assumptions that need attention>
```
