import unittest
import pandas as pd
from helpers import categorize


def make_pr_states(mapping):
    return pd.Series(mapping)


class TestCategorize(unittest.TestCase):

    def test_unknown_pr_returns_no_reviews(self):
        pr_states = make_pr_states({1: {'APPROVED'}})
        self.assertEqual(categorize(999, pr_states), 'no_reviews')

    def test_empty_set_returns_no_reviews(self):
        pr_states = make_pr_states({1: set()})
        self.assertEqual(categorize(1, pr_states), 'no_reviews')

    def test_commented_only(self):
        pr_states = make_pr_states({1: {'COMMENTED'}})
        self.assertEqual(categorize(1, pr_states), 'commented_only')

    def test_approved_only(self):
        pr_states = make_pr_states({1: {'APPROVED'}})
        self.assertEqual(categorize(1, pr_states), 'approved_only')

    def test_approved_only_ignores_comment(self):
        pr_states = make_pr_states({1: {'APPROVED', 'COMMENTED'}})
        self.assertEqual(categorize(1, pr_states), 'approved_only')

    def test_changes_requested_then_approved(self):
        pr_states = make_pr_states({1: {'APPROVED', 'CHANGES_REQUESTED'}})
        self.assertEqual(categorize(1, pr_states), 'changes_requested_then_approved')

    def test_dismissed_then_approved(self):
        pr_states = make_pr_states({1: {'APPROVED', 'DISMISSED'}})
        self.assertEqual(categorize(1, pr_states), 'dismissed_then_approved')

    def test_changes_requested_and_dismissed_then_approved(self):
        pr_states = make_pr_states({1: {'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'}})
        self.assertEqual(categorize(1, pr_states), 'changes_requested_and_dismissed_then_approved')

    def test_changes_requested_no_approval(self):
        pr_states = make_pr_states({1: {'CHANGES_REQUESTED'}})
        self.assertEqual(categorize(1, pr_states), 'changes_requested_no_approval')

    def test_changes_requested_no_approval_with_comment(self):
        pr_states = make_pr_states({1: {'CHANGES_REQUESTED', 'COMMENTED'}})
        self.assertEqual(categorize(1, pr_states), 'changes_requested_no_approval')

    def test_dismissed_no_approval(self):
        pr_states = make_pr_states({1: {'DISMISSED'}})
        self.assertEqual(categorize(1, pr_states), 'dismissed_no_approval')

    def test_dismissed_no_approval_with_comment(self):
        pr_states = make_pr_states({1: {'DISMISSED', 'COMMENTED'}})
        self.assertEqual(categorize(1, pr_states), 'dismissed_no_approval')

    def test_both_problematic_revised_categories(self):
        pr_states = make_pr_states({
            1: {'APPROVED', 'CHANGES_REQUESTED'},
            2: {'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'},
        })
        problematic_revised = {
            'changes_requested_then_approved',
            'changes_requested_and_dismissed_then_approved',
        }
        self.assertIn(categorize(1, pr_states), problematic_revised)
        self.assertIn(categorize(2, pr_states), problematic_revised)


if __name__ == '__main__':
    unittest.main()
