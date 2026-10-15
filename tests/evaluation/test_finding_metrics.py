import unittest
from backend.evaluation.schemas import ExpectedFinding
from backend.evaluation.metrics.finding_metrics import evaluate_findings

class TestFindingMetrics(unittest.TestCase):
    """Deterministic unit tests for finding matching and classification metrics."""

    def test_exact_match_true_positive(self):
        expected = [
            ExpectedFinding(category="FTC_DISCLOSURE", severity="FAIL", rule_id="FTC_16_CFR_255")
        ]
        actual = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL", "description": "Missing disclosure"}
        ]
        res = evaluate_findings(expected, actual, case_id="test_case")

        self.assertEqual(res.true_positives, 1)
        self.assertEqual(res.false_positives, 0)
        self.assertEqual(res.false_negatives, 0)
        self.assertEqual(res.precision, 1.0)
        self.assertEqual(res.recall, 1.0)
        self.assertEqual(res.f1_score, 1.0)
        self.assertEqual(len(res.discrepancies), 0)

    def test_false_positive(self):
        expected = []
        actual = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL", "description": "False alarm"}
        ]
        res = evaluate_findings(expected, actual, case_id="test_case")

        self.assertEqual(res.true_positives, 0)
        self.assertEqual(res.false_positives, 1)
        self.assertEqual(res.false_negatives, 0)
        self.assertEqual(res.precision, 0.0)
        self.assertEqual(res.recall, 1.0)
        self.assertEqual(res.f1_score, 0.0)
        self.assertEqual(len(res.discrepancies), 1)
        self.assertEqual(res.discrepancies[0].failure_type, "FALSE_POSITIVE")

    def test_false_negative(self):
        expected = [
            ExpectedFinding(category="HEALTH_CLAIM", severity="FAIL")
        ]
        actual = []
        res = evaluate_findings(expected, actual, case_id="test_case")

        self.assertEqual(res.true_positives, 0)
        self.assertEqual(res.false_positives, 0)
        self.assertEqual(res.false_negatives, 1)
        self.assertEqual(res.precision, 0.0)
        self.assertEqual(res.recall, 0.0)
        self.assertEqual(res.f1_score, 0.0)
        self.assertEqual(len(res.discrepancies), 1)
        self.assertEqual(res.discrepancies[0].failure_type, "FALSE_NEGATIVE")

    def test_severity_mismatch(self):
        expected = [
            ExpectedFinding(category="FTC_DISCLOSURE", severity="FAIL")
        ]
        actual = [
            {"category": "FTC_DISCLOSURE", "severity": "WARNING", "description": "Ambiguous"}
        ]
        res = evaluate_findings(expected, actual, case_id="test_case")

        self.assertEqual(res.true_positives, 0)
        self.assertEqual(res.false_positives, 1)
        self.assertEqual(res.false_negatives, 1)
        self.assertEqual(res.f1_score, 0.0)
        self.assertTrue(any(d.failure_type == "SEVERITY_MISMATCH" for d in res.discrepancies))

    def test_both_empty_sets(self):
        res = evaluate_findings([], [], case_id="test_case")
        self.assertEqual(res.true_positives, 0)
        self.assertEqual(res.false_positives, 0)
        self.assertEqual(res.false_negatives, 0)
        self.assertEqual(res.precision, 1.0)
        self.assertEqual(res.recall, 1.0)
        self.assertEqual(res.f1_score, 1.0)
        self.assertEqual(len(res.discrepancies), 0)

    def test_multiple_findings_partial_overlap(self):
        expected = [
            ExpectedFinding(category="FTC_DISCLOSURE", severity="FAIL"),
            ExpectedFinding(category="HEALTH_CLAIM", severity="FAIL")
        ]
        actual = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL"},
            {"category": "BRAND_SAFETY", "severity": "WARNING"}
        ]
        res = evaluate_findings(expected, actual, case_id="test_case")

        self.assertEqual(res.true_positives, 1)
        self.assertEqual(res.false_positives, 1)
        self.assertEqual(res.false_negatives, 1)
        self.assertEqual(res.precision, 0.5)
        self.assertEqual(res.recall, 0.5)
        self.assertEqual(res.f1_score, 0.5)

if __name__ == "__main__":
    unittest.main()
