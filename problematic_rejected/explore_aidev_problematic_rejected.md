# explore_aidev_problematic_rejected — Summary

## Goal

Build a clean, focused cohort of **AI-generated pull requests that were rejected by human reviewers** from the `hao-li/AIDev` HuggingFace dataset, and prepare supporting data for downstream analysis.

---

## Pipeline

### 1. Data loading
Six Parquet tables are pulled from the dataset:

| Table | Contents |
|---|---|
| `pull_request` | PR metadata: title, agent, repo, timestamps |
| `pr_commits` | Commits attached to each PR |
| `pr_reviews` | Formal review events (APPROVED, CHANGES_REQUESTED, etc.) |
| `pr_review_comments_v2` | Inline diff comments from reviews |
| `pr_timeline` | Full event timeline per PR |
| `pr_commit_details` | Per-file change details for every commit |

### 2. Baseline: closed-without-merge
A PR is initially considered **rejected** if `merged_at` is null and `closed_at` is non-null.  
**Raw count: 7,270 PRs.**

### 3. Review-category classification
Each PR's review history is classified into a category (e.g. `changes_requested_no_approval`, `commented_only`, `no_reviews`, …) using the `categorize()` helper from `helpers.py`.

### 4. Filter cascade

| Step | Criterion | Remaining |
|---|---|---|
| Baseline | closed, not merged | 7,270 |
| Has at least one review | exclude `no_reviews` | 1,384 |
| Not a quick-close | open ≥ 60 seconds | 1,370 |
| Small scope | < 10 distinct files changed | 914 |
| Human rejection signal | at least one human `CHANGES_REQUESTED` review | **139** |

### 5. Supporting subsets
Three filtered DataFrames are derived from the final 139-PR cohort:

- **`pr_reviews_sub`** — 622 reviews on these PRs
- **`pr_commits_sub`** — 784 commits on these PRs
- **`cr_inline_comments`** — 326 inline comments from human `CHANGES_REQUESTED` reviews (covering 80 of the 139 PRs), with `pr_id` joined in

### 6. Final cohort breakdown

| Review category | Count |
|---|---|
| `changes_requested_no_approval` | 121 |
| `changes_requested_then_approved` | 17 |
| `changes_requested_and_dismissed_then_approved` | 1 |
| **Total** | **139** |

### 7. Spot-check cell
Lets you inspect any single PR end-to-end: metadata, reviews, commits (with GitHub URLs), and inline CR comments.

---

## Key design decisions

- **"Quick-close" exclusion (< 60 s):** removes accidental or automated closures that don't represent genuine human rejection.
- **Scope cap (< 10 files):** keeps the cohort tractable and filters out large refactors where rejection signals are noisier.
- **Human-only rejection signal:** bot `CHANGES_REQUESTED` events are excluded to ensure the rejection came from a real reviewer.
