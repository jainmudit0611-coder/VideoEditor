import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.graph.state import (
    ComplianceFinding,
    AuditPlan,
    AuditPlanCheck,
    VerificationOutcome,
    VerificationResult,
    PolicyCitation,
    VideoEvidence,
    VideoAuditState
)

class TestStateSchemas(unittest.TestCase):
    def test_compliance_finding_validation(self):
        finding = ComplianceFinding(
            rule_category="FTC_DISCLOSURE",
            status="FAIL",
            severity="CRITICAL",
            description="Missing sponsorship disclosure",
            reasoning="Video contains sponsored product mention without clear disclosure.",
            policy_evidence=PolicyCitation(
                document="1001a-influencer-guide-508_1.pdf",
                content="Influencers must clearly disclose material connections."
            ),
            video_evidence=VideoEvidence(
                text="Trying out this awesome product sent to me!",
                evidence_type="TRANSCRIPT"
            ),
            confidence=0.95
        )
        self.assertEqual(finding.rule_category, "FTC_DISCLOSURE")
        self.assertEqual(finding.status, "FAIL")
        self.assertEqual(finding.severity, "CRITICAL")
        self.assertEqual(finding.confidence, 0.95)

    def test_audit_plan_schema(self):
        plan = AuditPlan(
            checks=[
                AuditPlanCheck(
                    area="sponsorship_disclosure",
                    rationale="Check for FTC disclosures",
                    evidence_needed=["POLICY", "TRANSCRIPT"]
                )
            ]
        )
        self.assertEqual(len(plan.checks), 1)
        self.assertEqual(plan.checks[0].area, "sponsorship_disclosure")

    def test_verification_outcome_schema(self):
        outcome = VerificationOutcome(
            overall_status="VERIFIED",
            results=[
                VerificationResult(
                    category="FTC_DISCLOSURE",
                    verified=True,
                    grounding_score=1.0,
                    reason="Grounding verified.",
                    action="VERIFIED"
                )
            ],
            feedback_summary="All checks passed."
        )
        self.assertEqual(outcome.overall_status, "VERIFIED")
        self.assertTrue(outcome.results[0].verified)

    def test_video_audit_state_dict(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_1234",
            "local_file_path": None,
            "video_metadata": {"duration": 30},
            "transcript": "Hello world",
            "ocr_text": ["BUY NOW"],
            "audit_plan": None,
            "retrieved_evidence": [],
            "evidence_requests": [],
            "audit_findings": [],
            "compliance_results": [],
            "citations": [],
            "verification_results": None,
            "verification_feedback": None,
            "iteration_count": 0,
            "confidence": 1.0,
            "final_status": "PASS",
            "final_report": "Clean",
            "errors": []
        }
        self.assertEqual(state["video_id"], "vid_1234")
        self.assertEqual(state["iteration_count"], 0)

if __name__ == "__main__":
    unittest.main()
