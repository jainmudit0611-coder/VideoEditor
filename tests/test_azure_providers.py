import unittest
from unittest.mock import MagicMock, patch, mock_open
import requests

from backend.src.services.vision_analyzer import VisionAnalyzerService, VisionAnalysisResult
from backend.src.services.video_indexer import VideoIndexerService
from backend.src.graph.tools import search_policy_rules
from backend.src.graph.state import VisualObservation
from backend.src.config import settings


class TestAzureVisionAnalyzer(unittest.TestCase):
    """
    Tests for Azure OpenAI Vision Analyzer Service.
    Labels: [AZURE OPENAI VISION / DEGRADED OCR FALLBACK]
    """

    def test_unconfigured_credentials_activates_degraded_fallback(self):
        service = VisionAnalyzerService(
            endpoint=None,
            api_key=None,
            deployment=None
        )
        self.assertFalse(service.is_configured)
        config_status = service.validate_config()
        self.assertEqual(config_status["status"], "blocked_by_credentials")
        self.assertEqual(config_status["fallback_mode"], "DEGRADED_OCR_FALLBACK")

        # Analyzing frames without credentials returns empty native observations and sets degraded mode
        frames = [{"frame_path": "dummy.jpg", "timestamp": 1.0}]
        ocr_items = [{"text": "Sponsored by BrandX", "start_time": 1.0, "end_time": 2.0}]

        observations, is_degraded = service.analyze_batch_frames(frames, ocr_items=ocr_items)
        self.assertTrue(is_degraded)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["mode"], "DEGRADED_OCR_FALLBACK")
        self.assertIn("Sponsored by BrandX", observations[0]["description"])

    @patch("backend.src.services.vision_analyzer.AzureChatOpenAI")
    def test_successful_native_vision_inference(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_chat_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured

        mock_structured.invoke.return_value = VisionAnalysisResult(
            observations=[
                VisualObservation(
                    timestamp=2.5,
                    category="disclosure",
                    description="Clear #ad on top right corner",
                    text_snippet="#ad",
                    is_prominent=True,
                    confidence=0.98
                )
            ]
        )

        service = VisionAnalyzerService(
            endpoint="https://mock-openai.openai.azure.com/",
            api_key="mock-key-secret-123456",
            deployment="gpt-4o"
        )
        self.assertTrue(service.is_configured)

        with patch.object(service, "encode_image_to_base64", return_value="base64dummy"):
            obs = service.analyze_frame("dummy_frame.jpg", 2.5)

        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["category"], "disclosure")
        self.assertEqual(obs[0]["mode"], "NATIVE_VISION")
        self.assertEqual(obs[0]["timestamp"], 2.5)
        self.assertIsNone(service.last_error_reason)

    @patch("backend.src.services.vision_analyzer.AzureChatOpenAI")
    def test_auth_failure_triggers_sanitized_handling(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_chat_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.invoke.side_effect = Exception("401 Unauthorized: Invalid API key")

        service = VisionAnalyzerService(
            endpoint="https://mock-openai.openai.azure.com/",
            api_key="bad-key",
            deployment="gpt-4o"
        )
        with patch.object(service, "encode_image_to_base64", return_value="base64dummy"):
            obs = service.analyze_frame("dummy.jpg", 1.0)

        self.assertEqual(len(obs), 0)
        self.assertEqual(service.last_error_reason, "AUTH_FAILURE")

    @patch("backend.src.services.vision_analyzer.AzureChatOpenAI")
    def test_rate_limit_triggers_sanitized_handling(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_chat_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.invoke.side_effect = Exception("429 RateLimitError: Requests per minute exceeded")

        service = VisionAnalyzerService(
            endpoint="https://mock-openai.openai.azure.com/",
            api_key="mock-key",
            deployment="gpt-4o"
        )
        with patch.object(service, "encode_image_to_base64", return_value="base64dummy"):
            obs = service.analyze_frame("dummy.jpg", 1.0)

        self.assertEqual(len(obs), 0)
        self.assertEqual(service.last_error_reason, "RATE_LIMITED")

    @patch("backend.src.services.vision_analyzer.AzureChatOpenAI")
    def test_timeout_triggers_sanitized_handling(self, mock_chat_cls):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_chat_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured
        mock_structured.invoke.side_effect = TimeoutError("Request timed out after 30.0s")

        service = VisionAnalyzerService(
            endpoint="https://mock-openai.openai.azure.com/",
            api_key="mock-key",
            deployment="gpt-4o"
        )
        with patch.object(service, "encode_image_to_base64", return_value="base64dummy"):
            obs = service.analyze_frame("dummy.jpg", 1.0)

        self.assertEqual(len(obs), 0)
        self.assertEqual(service.last_error_reason, "TIMEOUT")


class TestAzureVideoIndexer(unittest.TestCase):
    """
    Tests for Azure Video Indexer Service.
    Labels: [AZURE VIDEO INDEXER / ARM TOKEN EXCHANGE]
    """

    def test_unconfigured_credentials_raises_clear_error(self):
        service = VideoIndexerService(
            account_id=None,
            location=None,
            subscription_id=None,
            resource_group=None
        )
        self.assertFalse(service.is_configured)
        config = service.validate_config()
        self.assertEqual(config["status"], "blocked_by_credentials")

        with self.assertRaises(RuntimeError) as ctx:
            service.get_access_token()
        self.assertIn("BLOCKED_BY_CREDENTIALS", str(ctx.exception))

        with self.assertRaises(RuntimeError) as ctx:
            service.upload_video("dummy.mp4", "test_video")
        self.assertIn("BLOCKED_BY_CREDENTIALS", str(ctx.exception))

    def test_time_parsing_helper(self):
        service = VideoIndexerService()
        self.assertEqual(service._parse_time("0:01:30"), 90.0)
        self.assertEqual(service._parse_time("00:45"), 45.0)
        self.assertEqual(service._parse_time("1:00:00"), 3600.0)
        self.assertEqual(service._parse_time("12.5"), 12.5)
        self.assertEqual(service._parse_time("invalid"), 0.0)

    def test_extract_data_structure(self):
        service = VideoIndexerService()
        sample_vi_json = {
            "videos": [
                {
                    "insights": {
                        "transcript": [
                            {
                                "text": "This video is sponsored by Acme.",
                                "speakerId": "Speaker 1",
                                "instances": [{"start": "0:00:05", "end": "0:00:10"}]
                            }
                        ],
                        "ocr": [
                            {
                                "text": "USE CODE: DISCOUNT20",
                                "instances": [{"start": "0:00:08", "end": "0:00:15"}]
                            }
                        ]
                    }
                }
            ],
            "summarizedInsights": {
                "duration": {"seconds": 30}
            }
        }
        result = service.extract_data(sample_vi_json)
        self.assertEqual(result["transcript"], "This video is sponsored by Acme.")
        self.assertEqual(len(result["transcript_items"]), 1)
        self.assertEqual(result["transcript_items"][0]["start_time"], 5.0)
        self.assertEqual(len(result["ocr_items"]), 1)
        self.assertEqual(result["ocr_items"][0]["text"], "USE CODE: DISCOUNT20")
        self.assertEqual(result["ocr_items"][0]["start_time"], 8.0)
        self.assertEqual(result["video_metadata"]["duration"], 30)

    @patch("backend.src.services.video_indexer.requests.post")
    def test_auth_failure_in_token_exchange(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        service = VideoIndexerService(
            account_id="acc-123",
            location="eastus",
            subscription_id="sub-123",
            resource_group="rg-123"
        )
        with self.assertRaises(RuntimeError) as ctx:
            service.get_account_token("fake_arm_token")
        self.assertIn("access denied", str(ctx.exception).lower())

    @patch("backend.src.services.video_indexer.requests.post")
    def test_rate_limit_in_upload(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        service = VideoIndexerService(
            account_id="acc-123",
            location="eastus",
            subscription_id="sub-123",
            resource_group="rg-123"
        )
        with patch.object(service, "get_access_token", return_value="arm_token"):
            with patch.object(service, "get_account_token", return_value="vi_token"):
                with patch("builtins.open", mock_open(read_data=b"fake video data")):
                    with self.assertRaises(RuntimeError) as ctx:
                        service.upload_video("test.mp4", "vid")
                    self.assertIn("rate limited", str(ctx.exception).lower())


class TestAzureAISearch(unittest.TestCase):
    """
    Tests for Azure AI Search Tool (search_policy_rules).
    Labels: [AZURE AI SEARCH / VECTOR RAG]
    """

    def test_unconfigured_credentials_returns_empty_fallback(self):
        with patch.dict("os.environ", {
            "AZURE_SEARCH_ENDPOINT": "",
            "AZURE_SEARCH_API_KEY": "",
            "AZURE_OPENAI_ENDPOINT": "",
            "AZURE_OPENAI_API_KEY": ""
        }, clear=False):
            # Must return empty list cleanly without throwing or injecting error docs
            results = search_policy_rules.invoke({"query": "FTC influencer disclosures"})
            self.assertEqual(results, [])

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_successful_search_returns_policy_documents(self, mock_emb_cls, mock_search_cls):
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "FTC requires clear and conspicuous disclosures for paid endorsements."
        mock_doc1.metadata = {"source": "FTC_Endorsement_Guides_2023.pdf"}

        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = [mock_doc1]
        mock_search_cls.return_value = mock_vector_store

        with patch.dict("os.environ", {
            "AZURE_SEARCH_ENDPOINT": "https://test-search.search.windows.net",
            "AZURE_SEARCH_API_KEY": "test-key-123",
            "AZURE_OPENAI_ENDPOINT": "https://test-openai.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key-456"
        }, clear=False):
            results = search_policy_rules.invoke({"query": "FTC disclosures"})
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["document"], "FTC_Endorsement_Guides_2023.pdf")
            self.assertIn("clear and conspicuous", results[0]["content"])

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_search_auth_failure_returns_clean_fallback(self, mock_emb_cls, mock_search_cls):
        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.side_effect = Exception("401 Unauthorized: Invalid API Key")
        mock_search_cls.return_value = mock_vector_store

        with patch.dict("os.environ", {
            "AZURE_SEARCH_ENDPOINT": "https://test-search.search.windows.net",
            "AZURE_SEARCH_API_KEY": "invalid-key",
            "AZURE_OPENAI_ENDPOINT": "https://test-openai.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key"
        }, clear=False):
            results = search_policy_rules.invoke({"query": "FTC disclosures"})
            self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
