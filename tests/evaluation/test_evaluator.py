import unittest
from backend.evaluation.schemas import EvaluationCase, ExpectedFinding, ExpectedEvidence, ExpectedCitation
from backend.evaluation.evaluator import AuditEvaluator

class TestEvaluator(unittest.TestCase):
    """Deterministic integration tests for AuditEvaluator."""

    def setUp(self):
        self.evaluator = AuditEvaluator()

    def test_evaluate_case_full_pass(self):
        case = EvaluationCase(
            case_id="case_test_01",
            description="Testing evaluator single case",
            video_url="https://youtube.com/watch?v=test",
            expected_findings=[
                ExpectedFinding(category="FTC_DISCLOSURE", severity="FAIL")
            ],
            expected_evidence=[
                ExpectedEvidence(type="TRANSCRIPT", contains="gifted product", timestamp="00:10")
            ],
            expected_citations=[
                ExpectedCitation(rule_category="FTC_DISCLOSURE", document_contains="FTC Guides")
            ],
            expected_verifier_status="VERIFIED"
        )

        audit_output = {
            "status": "FAIL",
            "final_report": "Audit report summary.",
            "compliance_results": [
                {
                    "category": "FTC_DISCLOSURE",
                    "severity": "FAIL",
                    "description": "Missing disclosure on gifted product",
                    "timestamp": "00:10"
                }
            ],
            "retrieved_evidence": [
                {
                    "type": "TRANSCRIPT",
                    "text": "The company sent this gifted product over for review",
                    "timestamp": "00:10"
                }
            ],
            "citations": [
                {
                    "rule_category": "FTC_DISCLOSURE",
                    "document": "FTC Guides Concerning Endorsements",
                    "content": "Must clearly disclose material connections."
                }
            ],
            "verification_summary": {
                "status": "VERIFIED"
            },
            "is_degraded_vision_mode": False
        }

        res = self.evaluator.evaluate_case(case, audit_output)

        self.assertEqual(res.case_id, "case_test_01")
        self.assertEqual(res.execution_mode, "NATIVE_VISION")
        self.assertEqual(res.finding_metrics.f1_score, 1.0)
        self.assertEqual(res.grounding_metrics.evidence_support_rate, 1.0)
        self.assertEqual(res.citation_metrics.citation_presence_rate, 1.0)
        self.assertTrue(res.schema_metrics.is_valid)
        self.assertEqual(res.verifier_metrics.status, "AGREED")
        self.assertEqual(len(res.discrepancies), 0)

    def test_evaluate_case_with_discrepancy(self):
        case = EvaluationCase(
            case_id="case_test_02",
            description="Testing evaluator discrepancy detection",
            video_url="https://youtube.com/watch?v=test2",
            expected_findings=[
                ExpectedFinding(category="FTC_DISCLOSURE", severity="FAIL")
            ],
            expected_evidence=[],
            expected_citations=[],
            expected_verifier_status="VERIFIED"
        )

        # Audit output produces a FALSE NEGATIVE (no findings reported)
        audit_output = {
            "status": "PASS",
            "final_report": "Clean report.",
            "compliance_results": [],
            "retrieved_evidence": [],
            "citations": [],
            "verification_summary": {
                "status": "VERIFIED"
            },
            "is_degraded_vision_mode": True
        }

        res = self.evaluator.evaluate_case(case, audit_output)

        self.assertEqual(res.execution_mode, "DEGRADED_OCR_FALLBACK")
        self.assertEqual(res.finding_metrics.false_negatives, 1)
        self.assertEqual(len(res.discrepancies), 1)
        self.assertEqual(res.discrepancies[0].failure_type, "FALSE_NEGATIVE")

if __name__ == "__main__":
    unittest.main()
