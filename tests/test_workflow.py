import sys
import os
import unittest

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.graph.workflow import route_after_verification, create_graph, MAX_AUDIT_ITERATIONS
from backend.src.graph.state import VideoAuditState

class TestWorkflowRouting(unittest.TestCase):
    def test_router_verified(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_123",
            "local_file_path": None,
            "video_metadata": {},
            "transcript": "Test",
            "ocr_text": [],
            "audit_plan": None,
            "retrieved_evidence": [],
            "evidence_requests": [],
            "audit_findings": [],
            "compliance_results": [],
            "citations": [],
            "verification_results": {
                "overall_status": "VERIFIED",
                "results": []
            },
            "verification_feedback": None,
            "iteration_count": 0,
            "confidence": 1.0,
            "final_status": "PASS",
            "final_report": "",
            "errors": []
        }

        next_node = route_after_verification(state)
        self.assertEqual(next_node, "report_generator")

    def test_router_needs_more_evidence_under_max_limit(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_123",
            "local_file_path": None,
            "video_metadata": {},
            "transcript": "Test",
            "ocr_text": [],
            "audit_plan": None,
            "retrieved_evidence": [],
            "evidence_requests": [],
            "audit_findings": [],
            "compliance_results": [],
            "citations": [],
            "verification_results": {
                "overall_status": "NEEDS_MORE_EVIDENCE",
                "results": []
            },
            "verification_feedback": "Missing citation",
            "iteration_count": 0,
            "confidence": 0.8,
            "final_status": "FAIL",
            "final_report": "",
            "errors": []
        }

        next_node = route_after_verification(state)
        self.assertEqual(next_node, "auditor")
        self.assertEqual(state["iteration_count"], 1)

    def test_router_max_iteration_fallback(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_123",
            "local_file_path": None,
            "video_metadata": {},
            "transcript": "Test",
            "ocr_text": [],
            "audit_plan": None,
            "retrieved_evidence": [],
            "evidence_requests": [],
            "audit_findings": [],
            "compliance_results": [],
            "citations": [],
            "verification_results": {
                "overall_status": "NEEDS_MORE_EVIDENCE",
                "results": []
            },
            "verification_feedback": "Still ungrounded",
            "iteration_count": MAX_AUDIT_ITERATIONS,
            "confidence": 0.5,
            "final_status": "FAIL",
            "final_report": "",
            "errors": []
        }

        next_node = route_after_verification(state)
        self.assertEqual(next_node, "report_generator")
        self.assertEqual(state["final_status"], "UNRESOLVED")

    def test_create_graph_compilation(self):
        app = create_graph()
        self.assertIsNotNone(app)

if __name__ == "__main__":
    unittest.main()
