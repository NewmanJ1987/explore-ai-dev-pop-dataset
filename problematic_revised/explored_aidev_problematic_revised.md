# AIDev — Problematic-Revised Subset Exploration

## Definition

**Problematic-Revised** PRs are gold candidates where a human reviewer explicitly requested changes and the agent subsequently revised the PR until it received approval and was merged.

These are the most valuable cases for studying agent responsiveness to reviewer feedback: the agent had to iterate.

---

## Derivation from `explore_aidev_pop.ipynb`

The review category breakdown of all **24,014 merged PRs** was:

| Category | Count |
|---|---|
| No reviews | 18,082 |
| Approved only | 3,444 |
| Commented only | 1,806 |
| **Changes requested → Approved** | **386** |
| Changes requested, no approval | 129 |
| Dismissed → Approved | 112 |
| **Changes requested + Dismissed → Approved** | **41** |
| Dismissed, no approval | 14 |

**Problematic-Revised (raw) = 386 + 41 = 427 cases**

---

## Filters Applied

Two noise filters are applied to the raw 427, implemented in `explore_aidev_problematic_revised.ipynb`:

1. **Remove bot-approved PRs** — `APPROVED` review must be from `user_type == 'User'`
   → 427 → **403**

2. **Require human `CHANGES_REQUESTED`** — `CHANGES_REQUESTED` review must also be from `user_type == 'User'`
   → 403 → **397**

---

## Clean Subset Summary

| Metric | Value |
|---|---|
| **Total PRs (clean)** | **397** |
| `changes_requested_then_approved` | 364 |
| `changes_requested_and_dismissed_then_approved` | 33 |
| PRs with inline CR comments | 300 |
| Total inline CR comments | 1,107 |
| Reviews on revised PRs | 3,079 |
| Commits on revised PRs | 3,107 |

---

## Squash Detection

Commit counts per PR were computed to identify squashed PRs (single-commit merges that hide the revision history):

| | Count |
|---|---|
| Non-squashed (>1 commit) | 390 |
| Likely squashed (1 commit) | 7 |

For non-squashed PRs, the commit count distribution: mean **7.9**, median **6**, max **30**.

---

## Dataset Schema Reminder

Relevant tables and fields for this subset:

| Table | Key Fields |
|---|---|
| `prs` | `id`, `agent`, `repo_url`, `created_at`, `merged_at` |
| `reviews` | `pr_id`, `state` (APPROVED / CHANGES_REQUESTED / COMMENTED / DISMISSED), `user_type`, `submitted_at` |
| `pr_review_comments_v2` | `pull_request_review_id`, `body`, `diff_hunk`, `path` |
| `commits` | `pr_id`, `sha`, `message`, `author` |
| `timeline` | `pr_id`, `event`, `created_at`, `actor` |

---

## What the Notebook Does

1. **Extracts the 427 raw PR ids** using `categorize()` from `helpers.py`
2. **Applies the two human-only filters** → 397 clean PRs
3. **Pulls inline review comments** from `CHANGES_REQUESTED` reviews → 300 PRs, 1,107 comments
4. **Computes commit counts** per PR to flag squashed revisions
5. **Samples a PR** for manual inspection (reviews, commits with URLs, inline CR comments)

---

## Remaining Considerations

- **Bot-only revisions**: commits after `CHANGES_REQUESTED` by bots (e.g., `github-actions[bot]`) rather than the agent are not yet filtered — worth checking per-commit `author`.
- **Trivial fix commits**: "fix typo", "bump version", "rebase" commits don't represent meaningful agent reasoning; could be excluded from revision cycle analysis.
- **Dismissed-then-approved group (33 cases)**: verify whether dismissals were legitimate bypasses or genuine review resolutions.

---

## Related Subsets (from `todo.md`)

| Subset | Count | Source |
|---|---|---|
| **Problematic-Revised** (this file) | 397 | Changes requested → revised → approved → merged |
| Problematic-Reject | 7,270 | Closed without merge |
| Accepted | 3,444 | At least one approval, merged |
| Merged, no approval | 20,031 | Merged with no formal review approval |
