import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.services.vision_analyzer import VisionAnalyzerService
from backend.src.graph.nodes import extract_multimodal_frames_node
from backend.src.graph.state import VideoAuditState

class TestHardening(unittest.TestCase):
    def test_degraded_mode_ocr_fallback(self):
        service = VisionAnalyzerService()
        ocr_items = [{"text": "#ad Sponsored", "start_time": 5.0, "end_time": 8.0}]
        
        obs, is_degraded = service.analyze_batch_frames([], ocr_items)
        self.assertTrue(is_degraded)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["mode"], "DEGRADED_OCR_FALLBACK")

    def test_cleanup_in_extract_frames_node_on_error(self):
        state: VideoAuditState = {
            "video_url": "https://youtu.be/test",
            "video_id": "vid_cleanup_test",
            "local_file_path": "non_existent_file.mp4",
            "video_metadata": {},
            "transcript": "Test",
            "ocr_text": [],
            "transcript_items": [],
            "ocr_items": [],
            "visual_observations": [],
            "extracted_frame_count": 0,
            "is_degraded_vision_mode": False,
            "timing_metrics": {},
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
            "final_report": "",
            "errors": []
        }

        # Should complete gracefully without raising unhandled exception
        res = extract_multimodal_frames_node(state)
        self.assertIsNone(res.get("local_file_path"))
        self.assertIn("vision_time", res.get("timing_metrics", {}))

if __name__ == "__main__":
    unittest.main()
