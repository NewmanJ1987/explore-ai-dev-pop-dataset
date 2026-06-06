# /compare-commits

Compares two commits on a GitHub PR against an existing assumptions file and writes a session notes file.

**Usage:** `/compare-commits <PR_URL> <FROM_SHA> <TO_SHA> <ASSUMPTIONS_FILE>`

Example:
```
/compare-commits https://github.com/owner/repo/pull/589 739bdc7e d8176c82 analysis/pr-589-assumptions.md
```

---

## Steps

1. Extract the repo path and PR number from `$PR_URL` (e.g. `owner/repo` and `589`).

2. Fetch the diff between the two commits:
   ```
   gh api repos/<owner>/<repo>/compare/<FROM_SHA>...<TO_SHA> --jq '.files[] | {filename, status, additions, deletions, patch}'
   ```

3. Read the assumptions file at `$ASSUMPTIONS_FILE`.

4. For each file in the diff, summarise what changed in plain language (ignore version bumps and lock file changes — note them as a group only).

5. For each assumption in the file, determine:
   - **Confirmed by diff** — the new code directly proves the assumption holds
   - **Assumption was wrong** — the diff shows the assumption's premise was incorrect
   - **Not visible in diff** — the relevant code is not in the changed files; cannot determine from this range alone

6. Write the output to `analysis/pr-<PR_NUMBER>-session.md`:

```
# PR #<PR_NUMBER> — Session Notes

## PR
<PR_URL>

## Commits compared
- From: `<FROM_SHA>`
- To:   `<TO_SHA>`

---

## What changed between the two commits

<one paragraph per changed file that matters — skip version bumps, group them as a single line>

---

## Impact on assumptions (source: <ASSUMPTIONS_FILE>)

For each assumption that was confirmed or found wrong, write one short paragraph.
End with a single sentence listing assumption numbers that could not be determined from this diff alone.
```

**Do not** read any files outside the diff. Do not fetch PR comments or the full codebase. If an assumption cannot be evaluated from the changed files, say so — do not speculate.
