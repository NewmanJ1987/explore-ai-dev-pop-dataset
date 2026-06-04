import pandas as pd


def build_pr_states(reviews, pr_ids):
    """Return a Series mapping pr_id -> set of review states for the given pr_ids."""
    subset = reviews[reviews['pr_id'].isin(pr_ids)]
    return subset.groupby('pr_id')['state'].apply(set)


def categorize(pr_id, pr_states):
    """Classify a merged PR by its review state history."""
    if pr_id not in pr_states.index:
        return 'no_reviews'
    states = pr_states[pr_id]
    has_approved  = 'APPROVED' in states
    has_changes   = 'CHANGES_REQUESTED' in states
    has_dismissed = 'DISMISSED' in states
    has_commented = 'COMMENTED' in states
    if not has_approved and not has_changes and not has_dismissed:
        return 'commented_only' if has_commented else 'no_reviews'
    if has_approved and not has_changes and not has_dismissed:
        return 'approved_only'
    if has_approved and has_changes and not has_dismissed:
        return 'changes_requested_then_approved'
    if has_approved and has_dismissed and not has_changes:
        return 'dismissed_then_approved'
    if has_approved and has_changes and has_dismissed:
        return 'changes_requested_and_dismissed_then_approved'
    if has_changes and not has_approved:
        return 'changes_requested_no_approval'
    if has_dismissed and not has_approved:
        return 'dismissed_no_approval'
    return 'other'
