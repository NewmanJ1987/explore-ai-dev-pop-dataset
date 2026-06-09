# Accepted PRs — Notebook Logic, Assumptions & Results

## Overview

This notebook identifies AI-generated pull requests from the `hao-li/AIDev` HuggingFace dataset that represent **clean acceptances** — merged by a human reviewer with no formal revision cycle. The pipeline progressively narrows a raw pool of 24,014 merged PRs down to a well-defined cohort of 1,503.

---

## Data Sources

Six tables are loaded from `hao-li/AIDev`:

| Table | Contents |
|---|---|
| `pull_request` | PR metadata — title, agent, repo, timestamps |
| `pr_commits` | Commits attached to each PR |
| `pr_reviews` | Formal review events (APPROVED, CHANGES_REQUESTED, DISMISSED, COMMENTED) |
| `pr_review_comments_v2` | Inline comments tied to specific diff hunks |
| `pr_timeline` | Full event timeline per PR |
| `pr_commit_details` | File-level diff details per commit (filename, patch) |

---

## Pipeline & Logic

### Step 1 — Start from merged PRs

All PRs with a non-null `merged_at` are taken as the base population.

**Result:** 24,014 merged PRs

**Review category distribution across merged PRs:**

| Category | Count |
|---|---|
| no_reviews | 18,082 |
| approved_only | 3,444 |
| commented_only | 1,806 |
| changes_requested_then_approved | 386 |
| changes_requested_no_approval | 129 |
| dismissed_then_approved | 112 |
| changes_requested_and_dismissed_then_approved | 41 |
| dismissed_no_approval | 14 |

The `categorize()` helper (from `helpers.py`) assigns each PR a category based on the *set* of review states seen across all its reviews. It looks only at which states appeared — not their order or count.

---

### Step 2 — Filter to `approved_only`

A PR is kept if its review category is `approved_only`, meaning:
- At least one `APPROVED` review exists, AND
- No `CHANGES_REQUESTED` or `DISMISSED` events appear at all

**Assumption:** `approved_only` is a reliable proxy for "accepted without revision". This excludes PRs that went through formal iteration cycles.

**Caveat:** `approved_only` does not mean zero discussion — a reviewer can leave `COMMENTED`-state reviews or inline comments within an `APPROVED` review without triggering a formal `CHANGES_REQUESTED`. This informal feedback is captured in the dataset but is not surfaced by the category alone (see Step 5).

**Result:** 3,444 PRs

---

### Step 3 — Remove bot-approved PRs

PRs where every `APPROVED` review was submitted by a bot (`user_type != 'User'`) are dropped.

**Assumption:** Bot approvals (e.g. automated CI reviewers, GitHub Actions bots) do not represent genuine human judgement. Keeping them would inflate the accepted cohort with auto-merged PRs that were never reviewed by a person.

**Result:** 3,434 PRs (10 dropped — bot-only approvals)

---

### Step 4 — Commit count analysis

Commit counts are computed per PR using `pr_commits`. Single-commit PRs may represent squashed merges — one commit contains all the work, making it impossible to see the iteration history. This is noted but **no filter is applied at this stage** — all PRs are retained regardless of commit count.

**Commit count distribution (3,434 PRs):**

| Statistic | Value |
|---|---|
| Mean | 4.76 commits |
| Median | 3 commits |
| 25th percentile | 2 commits |
| 75th percentile | 6 commits |
| Max | 30 commits |

---

### Step 5 — Filter by files changed (2–9 files)

Distinct filenames are counted per PR across all commits using `pr_commit_details`. PRs are then bucketed and filtered to keep only those touching 2–9 distinct files.

**Files-changed distribution (before filter):**

| Bucket | Count | % |
|---|---|---|
| 1 file | 890 | 25.9% |
| 2–4 files | 1,019 | 29.7% |
| 5–9 files | 484 | 14.1% |
| 10+ files | 1,041 | 30.3% |

**Assumptions behind the filter:**
- **Lower bound (exclude 1-file PRs):** Single-file changes are too small to represent meaningful AI-authored contributions and may be trivial fixes (typos, config tweaks) rather than substantive code generation.
- **Upper bound (exclude 10+ file PRs):** Large multi-file PRs make it harder to isolate what the AI did, increase noise in analysis, and are more likely to involve scaffolding or mass renaming rather than intentional logic.
- The 2–9 range targets PRs of moderate scope — enough to show the AI reasoning across multiple files but focused enough to analyse.

**Result:** 1,503 PRs retained (1,931 dropped — 890 single-file + 1,041 with 10+ files)

---

### Step 6 — Human comment count & filter (≤ 1 comment)

Human comments are counted per PR from two sources:
1. **`COMMENTED`-state reviews** where `user_type == 'User'` — each counts as 1
2. **Inline review comments** (`pr_review_comments_v2`) attached to any review by a human reviewer

These are summed to give `n_human_comments` per PR. PRs with **2 or more** human comments are then dropped.

**Human comment distribution (1,503 PRs):**

| Comments | Count | % |
|---|---|---|
| 0 | 994 | 66.1% |
| 1 | 39 | 2.6% |
| 2+ | 470 | 31.3% |

**Why filter at 2+ comments?**

The `approved_only` category captures the *formal* review state but misses informal iteration. In practice, PRs with multiple reviewer comments often exhibit the same back-and-forth revision cycle as formally-requested changes — the reviewer leaves suggestions, the AI agent responds with updated commits, and the PR converges to an acceptable state. The only difference is that the reviewer never clicked "Request Changes". These PRs are not genuinely clean acceptances; they are informal revision cycles that happen to lack a CHANGES_REQUESTED event.

Keeping PRs with 0 or 1 human comment filters out this informal iteration pattern while still allowing for the occasional short clarifying remark that did not trigger any code changes.

**Result after filter:** 1,033 PRs (470 dropped with 2+ comments)

---

### Step 7 — Final cohort summary

**1,033 PRs** — merged, human-approved, 2–9 files changed, ≤ 1 human comment.

**Agent breakdown:**

| Agent | Count | % |
|---|---|---|
| Copilot | 568 | 37.8% |
| Devin | 488 | 32.5% |
| OpenAI Codex | 309 | 20.6% |
| Cursor | 116 | 7.7% |
| Claude Code | 22 | 1.5% |

---

## Key Assumptions Summary

| # | Assumption | Rationale |
|---|---|---|
| 1 | `approved_only` = accepted without revision | No CHANGES_REQUESTED or DISMISSED in the review set |
| 2 | Bot approvals are not genuine acceptances | Bot `user_type` flags automated, non-human review |
| 3 | 1-file PRs are too small to be meaningful | Too trivial; not representative of AI code generation |
| 4 | 10+ file PRs are too large/noisy | Hard to isolate intent; more likely to be scaffolding |
| 5 | `n_human_comments` captures all human feedback | Combines COMMENTED reviews + inline comments from `user_type == 'User'` |
| 6 | `approved_only` does not mean zero discussion | COMMENTED-state reviews exist alongside APPROVED events and are counted separately |
| 7 | 2+ comments signals informal revision, not clean acceptance | Reviewers with multiple comments tend to drive code changes even without a formal CHANGES_REQUESTED — the PR converges through informal back-and-forth rather than a clean first-pass approval |
| 7 | File count via `pr_commit_details` deduplicates across commits | A file touched in multiple commits counts once |

---

## Spot-Check Example

The zero-comment subset sample (random_state=42) surfaces **PR #1015** from `liam-hq/liam` — a Devin-authored refactor that removed redundant payload parameters from a Trigger.dev task. It received two APPROVED reviews from human reviewers with no comments left, merged within 25 hours of opening.

```
PR:      Refactor createKnowledgeSuggestionTask to reduce payload parameters
Agent:   Devin
Repo:    liam-hq/liam
Created: 2025-03-27  Merged: 2025-03-28

Reviews:
  APPROVED  MH4GF     User  2025-03-27T10:21:09Z
  APPROVED  junkisai  User  2025-03-28T10:28:39Z

Commits: 1 (squashed)
  893a397b — Refactor createKnowledgeSuggestionTask to reduce payload parameters
              Co-Authored-By: hirotaka.miyagi@route06.co.jp

Review Comments (top-level): none
Inline Review Comments:       none
```

This is the prototypical accepted PR: single-commit, two human approvals, no discussion, merged quickly.
