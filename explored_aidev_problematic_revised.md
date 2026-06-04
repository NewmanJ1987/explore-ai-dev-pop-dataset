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

**Problematic-Revised = 386 + 41 = 427 cases**

These are the two categories where a `CHANGES_REQUESTED` state was present and the PR was eventually approved and merged. The `dismissed_and_changes_requested_then_approved` group includes cases where some reviews were dismissed (e.g., by the agent re-pushing) but at least one human ultimately approved.

---

## Key Characteristics

- **427 total cases** (~1.8% of all merged PRs)
- All are **merged** — the revision process succeeded
- All have **at least one human APPROVED** review after a `CHANGES_REQUESTED` review
- The agent/developer had to make additional commits in response to reviewer feedback

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

## Filtering Considerations

Before using this subset, filter out noise:

1. **Bot-only revisions**: if the additional commits after `CHANGES_REQUESTED` were made by a bot (e.g., `github-actions[bot]`, `copilot-swe-agent[bot]`) rather than the agent, the "revision" is not substantive agent behaviour.

2. **Trivial fixes**: commits with messages like "fix typo", "bump version", "rebase" — these don't represent meaningful agent reasoning in response to review.

3. **Dismissals that skip the review**: if a `CHANGES_REQUESTED` was dismissed without addressing the feedback, that PR should not be counted as a genuine revision cycle. The `changes_requested_and_dismissed_then_approved` group (41 cases) needs inspection to check whether dismissals were legitimate.

4. **Self-approvals**: verify `user_type == 'User'` for APPROVED reviews (the dataset includes bot reviewers such as `copilot-pull-request-reviewer[bot]` and `coderabbitai[bot]`).

---

## Suggested Next Steps

1. **Extract the 427 PR ids** using the `categorize()` logic from the notebook:
   ```python
   revised_prs = merged_copy[
       merged_copy['review_category'].isin([
           'changes_requested_then_approved',
           'changes_requested_and_dismissed_then_approved'
       ])
   ]
   ```

2. **Reconstruct revision cycles**: for each PR, order all reviews and commits by timestamp to identify which commits were pushed *after* the `CHANGES_REQUESTED` review — these are the agent's revisions.

3. **Extract inline review comments** (`rev_cmts`) associated with the `CHANGES_REQUESTED` reviews to understand *what* the reviewer asked the agent to fix.

4. **Apply noise filters** (see above) and count the clean subset.

5. **Sample and manually inspect** 20–30 cases to validate that the revision was substantive and agent-driven.

---

## Related Subsets (from `todo.md`)

| Subset | Count | Source |
|---|---|---|
| **Problematic-Revised** (this file) | 427 | Changes requested → revised → approved → merged |
| Problematic-Reject | 7,270 | Closed without merge |
| Accepted | 3,444 | At least one approval, merged |
| Merged, no approval | 20,031 | Merged with no formal review approval |
