import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.graph.tools import (
    search_transcript_evidence,
    search_ocr_evidence,
    check_rule_compliance,
    search_policy_rules
)

class TestTools(unittest.TestCase):
    def test_search_transcript_evidence(self):
        transcript = "Hello everyone. Today I am promoting a sponsored product. Thanks to our sponsor XYZ."
        results = search_transcript_evidence.invoke({
            "query": "sponsored sponsor",
            "transcript_text": transcript
        })
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["evidence_type"], "TRANSCRIPT")
        self.assertIn("sponsor", results[0]["text"].lower())

    def test_search_ocr_evidence(self):
        ocr_lines = ["WELCOME TO MY CHANNEL", "PAID PROMOTION WITH BRAND", "LIKE AND SUBSCRIBE"]
        results = search_ocr_evidence.invoke({
            "query": "paid promotion",
            "ocr_lines": ocr_lines
        })
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["evidence_type"], "OCR")
        self.assertEqual(results[0]["text"], "PAID PROMOTION WITH BRAND")

    def test_check_rule_compliance(self):
        policy_text = "Influencers must disclose paid promotion clearly at the beginning of the video."
        finding = "No paid promotion disclosure was identified at the beginning of the video."
        
        res = check_rule_compliance.invoke({
            "rule_category": "FTC_DISCLOSURE",
            "finding_description": finding,
            "policy_text": policy_text
        })
        self.assertTrue(res["grounded"])
        self.assertGreater(res["grounding_score"], 0.3)

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_search_policy_rules_mock(self, mock_embeddings, mock_azure_search):
        mock_doc = MagicMock()
        mock_doc.page_content = "Disclosures must be clear and conspicuous."
        mock_doc.metadata = {"source": "1001a-influencer-guide-508_1.pdf"}
        
        mock_search_instance = MagicMock()
        mock_search_instance.similarity_search.return_value = [mock_doc]
        mock_azure_search.return_value = mock_search_instance
        
        results = search_policy_rules.invoke({"query": "FTC disclosure"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["document"], "1001a-influencer-guide-508_1.pdf")
        self.assertIn("clear and conspicuous", results[0]["content"])

if __name__ == "__main__":
    unittest.main()
