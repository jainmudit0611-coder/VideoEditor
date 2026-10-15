import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.services.vision_analyzer import VisionAnalyzerService

class TestVisionAnalyzerService(unittest.TestCase):
    def test_analyze_batch_frames_ocr_fallback(self):
        service = VisionAnalyzerService()
        ocr_items = [
            {"text": "#ad Sponsorship Disclosure", "start_time": 10.5, "end_time": 12.0}
        ]
        
        # When no vision API frames exist, fallback to OCR temporal observations
        obs, is_degraded = service.analyze_batch_frames([], ocr_items)
        self.assertTrue(is_degraded)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["timestamp"], 10.5)
        self.assertEqual(obs[0]["category"], "disclosure")
        self.assertIn("#ad", obs[0]["text"])

    @patch("backend.src.services.vision_analyzer.AzureChatOpenAI")
    def test_analyze_frame_mock(self, mock_llm):
        service = VisionAnalyzerService()
        service.api_key = "test_key"
        service.endpoint = "https://test.openai.azure.com/"
        
        mock_result = MagicMock()
        mock_obs = MagicMock()
        mock_obs.model_dump.return_value = {
            "timestamp": 5.0,
            "category": "disclosure",
            "description": "Visual disclosure text #ad visible in lower corner",
            "text": "#ad",
            "visible": True,
            "confidence": 0.95
        }
        mock_result.observations = [mock_obs]
        
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_result
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_result
        mock_instance.with_structured_output.return_value = mock_structured
        mock_llm.return_value = mock_instance
        
        with patch.object(service, "encode_image_to_base64", return_value="base64string"):
            obs = service.analyze_frame("dummy_path.jpg", 5.0)
            self.assertEqual(len(obs), 1)
            self.assertEqual(obs[0]["category"], "disclosure")
            self.assertEqual(obs[0]["timestamp"], 5.0)

if __name__ == "__main__":
    unittest.main()
