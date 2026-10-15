import sys
import os
import unittest

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.graph.nodes import verify_findings_node
from backend.src.graph.state import VideoAuditState

class TestVerifierNode(unittest.TestCase):
    def test_verify_findings_grounded(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_test",
            "local_file_path": None,
            "video_metadata": {},
            "transcript": "Check out this sponsored product from Acme.",
            "ocr_text": ["SPONSORED"],
            "audit_plan": None,
            "retrieved_evidence": [],
            "evidence_requests": [],
            "audit_findings": [
                {
                    "rule_category": "FTC_DISCLOSURE",
                    "status": "FAIL",
                    "severity": "HIGH",
                    "description": "Clear disclosure missing",
                    "reasoning": "Product mentioned without explicit verbal disclosure.",
                    "policy_evidence": {
                        "document": "influencer_guide.pdf",
                        "content": "Influencers must clearly disclose sponsored content."
                    },
                    "video_evidence": {
                        "text": "Check out this sponsored product from Acme",
                        "evidence_type": "TRANSCRIPT"
                    }
                }
            ],
            "compliance_results": [],
            "citations": [],
            "verification_results": None,
            "verification_feedback": None,
            "iteration_count": 0,
            "confidence": 1.0,
            "final_status": "FAIL",
            "final_report": "",
            "errors": []
        }

        res = verify_findings_node(state)
        v_results = res.get("verification_results", {})
        self.assertEqual(v_results.get("overall_status"), "VERIFIED")
        self.assertEqual(len(v_results.get("results", [])), 1)
        self.assertTrue(v_results["results"][0]["verified"])

    def test_verify_findings_missing_policy_citation(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_test",
            "local_file_path": None,
            "video_metadata": {},
            "transcript": "I love this item.",
            "ocr_text": [],
            "audit_plan": None,
            "retrieved_evidence": [],
            "evidence_requests": [],
            "audit_findings": [
                {
                    "rule_category": "FTC_DISCLOSURE",
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "description": "Alleged disclosure failure",
                    "reasoning": "Unsubstantiated claim",
                    "policy_evidence": None,  # Missing citation!
                    "video_evidence": {
                        "text": "I love this item",
                        "evidence_type": "TRANSCRIPT"
                    }
                }
            ],
            "compliance_results": [],
            "citations": [],
            "verification_results": None,
            "verification_feedback": None,
            "iteration_count": 0,
            "confidence": 1.0,
            "final_status": "FAIL",
            "final_report": "",
            "errors": []
        }

        res = verify_findings_node(state)
        v_results = res.get("verification_results", {})
        self.assertEqual(v_results.get("overall_status"), "NEEDS_MORE_EVIDENCE")
        self.assertFalse(v_results["results"][0]["verified"])
        self.assertIn("without attaching explicit policy citation", v_results["results"][0]["reason"])

if __name__ == "__main__":
    unittest.main()
