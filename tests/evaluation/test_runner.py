import unittest
from pathlib import Path
from backend.evaluation.runner import (
    load_evaluation_cases,
    load_case_audit_output,
    EvaluationSuiteRunner,
    generate_markdown_report,
)

class TestEvaluationRunner(unittest.TestCase):
    """Deterministic tests for EvaluationSuiteRunner and reporting."""

    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.cases_dir = self.project_root / "backend" / "evaluation" / "cases"
        self.fixtures_dir = self.project_root / "backend" / "evaluation" / "fixtures"

    def test_load_evaluation_cases(self):
        cases = load_evaluation_cases(self.cases_dir)
        self.assertGreaterEqual(len(cases), 5)
        case_ids = [c.case_id for c in cases]
        self.assertIn("case_001", case_ids)
        self.assertIn("case_002", case_ids)

    def test_load_case_audit_output(self):
        output = load_case_audit_output(self.fixtures_dir, "case_001")
        self.assertIsNotNone(output)
        self.assertIn("status", output)
        self.assertIn("compliance_results", output)

    def test_run_suite_metrics_and_markdown(self):
        cases = load_evaluation_cases(self.cases_dir)
        runner = EvaluationSuiteRunner()
        summary = runner.run_suite(cases, self.fixtures_dir, run_id="test_run_01")

        self.assertEqual(summary.evaluation_run_id, "test_run_01")
        self.assertEqual(summary.n_cases, len(cases))
        self.assertIn("finding_precision", summary.aggregate_metrics)
        self.assertIn("finding_recall", summary.aggregate_metrics)
        self.assertIn("finding_f1", summary.aggregate_metrics)
        self.assertIn("evidence_support_rate", summary.aggregate_metrics)
        self.assertIn("schema_validity_rate", summary.aggregate_metrics)

        # Generate markdown report
        md = generate_markdown_report(summary)
        self.assertIn("# Brand Guardian AI — Evaluation Report", md)
        self.assertIn("Finding Precision", md)
        self.assertIn("Finding Recall", md)
        self.assertIn("Evidence Support Rate", md)
        self.assertIn("Detailed Case Breakdown", md)
        self.assertIn("Limitations & Scientific Constraints", md)

if __name__ == "__main__":
    unittest.main()
