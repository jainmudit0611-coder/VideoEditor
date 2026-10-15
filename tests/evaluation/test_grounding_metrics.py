import unittest
from backend.evaluation.schemas import ExpectedEvidence
from backend.evaluation.metrics.grounding_metrics import evaluate_grounding

class TestGroundingMetrics(unittest.TestCase):
    """Deterministic unit tests for multimodal evidence grounding metrics."""

    def test_supported_transcript_evidence_with_timestamp(self):
        expected_ev = [
            ExpectedEvidence(type="TRANSCRIPT", contains="sponsored by BrandX", timestamp="00:03")
        ]
        actual_ev = [
            {"type": "TRANSCRIPT", "text": "This video is sponsored by BrandX today", "timestamp": "00:03"}
        ]
        actual_findings = [
            {"category": "FTC_DISCLOSURE", "severity": "PASS", "timestamp": "00:03"}
        ]
        res = evaluate_grounding(expected_ev, actual_ev, actual_findings, is_degraded_vision_mode=False)

        self.assertEqual(res.total_findings, 1)
        self.assertEqual(res.supported_findings, 1)
        self.assertEqual(res.unsupported_findings, 0)
        self.assertEqual(res.evidence_support_rate, 1.0)
        self.assertEqual(res.transcript_matches, 1)

    def test_supported_ocr_evidence_normalized_match(self):
        expected_ev = [
            ExpectedEvidence(type="OCR", contains="Paid Partnership", timestamp="00:02")
        ]
        actual_ev = [
            {"type": "OCR", "text": "PAID PARTNERSHIP WITH BRANDX", "timestamp": "00:02"}
        ]
        actual_findings = [
            {"category": "FTC_DISCLOSURE", "severity": "PASS", "timestamp": "00:02"}
        ]
        res = evaluate_grounding(expected_ev, actual_ev, actual_findings, is_degraded_vision_mode=False)

        self.assertEqual(res.ocr_matches, 1)
        self.assertEqual(res.evidence_support_rate, 1.0)

    def test_unsupported_finding_missing_timestamp_and_evidence(self):
        expected_ev = []
        actual_ev = []
        actual_findings = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL"}  # no timestamp, no evidence items
        ]
        res = evaluate_grounding(expected_ev, actual_ev, actual_findings, is_degraded_vision_mode=False)

        self.assertEqual(res.total_findings, 1)
        self.assertEqual(res.supported_findings, 0)
        self.assertEqual(res.unsupported_findings, 1)
        self.assertEqual(res.evidence_support_rate, 0.0)
        self.assertEqual(res.unsupported_finding_rate, 1.0)

    def test_missing_transcript_phrase(self):
        expected_ev = [
            ExpectedEvidence(type="TRANSCRIPT", contains="completely cures cancer", timestamp="00:15")
        ]
        actual_ev = [
            {"type": "TRANSCRIPT", "text": "our product helps support joint wellness", "timestamp": "00:15"}
        ]
        actual_findings = [
            {"category": "HEALTH_CLAIM", "severity": "FAIL", "timestamp": "00:15"}
        ]
        res = evaluate_grounding(expected_ev, actual_ev, actual_findings, is_degraded_vision_mode=False)

        self.assertEqual(res.transcript_matches, 0)

    def test_degraded_vision_mode_status(self):
        expected_ev = [
            ExpectedEvidence(type="VISUAL", contains="logo on lower right corner")
        ]
        actual_ev = []
        actual_findings = []
        res = evaluate_grounding(expected_ev, actual_ev, actual_findings, is_degraded_vision_mode=True)

        self.assertEqual(res.visual_evaluation_status, "NOT_AVAILABLE")

if __name__ == "__main__":
    unittest.main()
