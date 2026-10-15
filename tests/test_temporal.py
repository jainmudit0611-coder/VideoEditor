import sys
import os
import unittest

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.services.video_indexer import VideoIndexerService
from backend.src.graph.tools import search_visual_evidence

class TestTemporalEvidence(unittest.TestCase):
    def test_parse_time_formats(self):
        vi = VideoIndexerService()
        self.assertEqual(vi._parse_time("0:00:12.40"), 12.4)
        self.assertEqual(vi._parse_time("0:01:30.00"), 90.0)
        self.assertEqual(vi._parse_time("1:00:00.00"), 3600.0)
        self.assertEqual(vi._parse_time("15.5"), 15.5)

    def test_search_visual_evidence_tool(self):
        obs = [
            {
                "timestamp": 12.5,
                "category": "disclosure",
                "description": "Visual hashtag #ad present on screen",
                "text": "#ad",
                "confidence": 0.95,
                "frame_path": "frame_12_5.jpg"
            }
        ]
        results = search_visual_evidence.invoke({
            "query": "#ad disclosure visual",
            "visual_observations": obs
        })
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["evidence_type"], "VISUAL")
        self.assertEqual(results[0]["start_time"], 12.5)

if __name__ == "__main__":
    unittest.main()
