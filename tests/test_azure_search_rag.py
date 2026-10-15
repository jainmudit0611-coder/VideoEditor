"""
Tests for Azure AI Search RAG Pipeline.
Verifies schema compatibility, indexing logic, vector retrieval, empty queries, and provider error classification.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from backend.src.graph.tools import search_policy_rules
from backend.scripts.index_documents import (
    ensure_index_schema,
    get_normalized_openai_endpoint,
)


class TestAzureAISearchRAG(unittest.TestCase):
    """
    Unit test suite for Azure AI Search RAG components.
    Labels: [AZURE AI SEARCH / VECTOR RAG / INDEXING]
    """

    def test_schema_definition_compatibility(self):
        """Verifies schema contains required fields for LangChain AzureSearch vector store."""
        with patch("backend.scripts.index_documents.SearchIndexClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            ensure_index_schema(
                endpoint="https://mock-search.search.windows.net",
                api_key="mock-key",
                index_name="test-index"
            )

            mock_client.create_or_update_index.assert_called_once()
            called_index = mock_client.create_or_update_index.call_args[0][0]

            field_names = [f.name for f in called_index.fields]
            self.assertIn("id", field_names)
            self.assertIn("content", field_names)
            self.assertIn("content_vector", field_names)
            self.assertIn("metadata", field_names)

            # Validate vector field parameters
            vector_field = next(f for f in called_index.fields if f.name == "content_vector")
            self.assertEqual(vector_field.vector_search_dimensions, 1536)
            self.assertEqual(vector_field.vector_search_profile_name, "myHnswProfile")

    def test_endpoint_normalization(self):
        """Verifies that Azure OpenAI Foundry path URLs are normalized to base host."""
        with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "https://test.services.ai.azure.com/api/projects/123/openai/v1/responses"}):
            normalized = get_normalized_openai_endpoint()
            self.assertEqual(normalized, "https://test.services.ai.azure.com")

        with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com"}):
            normalized = get_normalized_openai_endpoint()
            self.assertEqual(normalized, "https://test.openai.azure.com")

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_retrieval_returns_structured_policy_evidence(self, mock_emb_cls, mock_vs_cls):
        """Verifies retrieval formats documents into the expected dictionary structure."""
        mock_vs = MagicMock()
        mock_vs_cls.return_value = mock_vs
        mock_vs.similarity_search.return_value = [
            Document(
                page_content="Influencers must clearly disclose brand relationships.",
                metadata={"source": "ftc_guidelines.pdf", "category": "influencer_disclosure"}
            ),
            Document(
                page_content="Disclosures must be placed above the fold.",
                metadata={"source": "ftc_guidelines.pdf", "category": "placement"}
            )
        ]

        results = search_policy_rules.invoke({"query": "influencer disclosure"})
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["document"], "ftc_guidelines.pdf")
        self.assertIn("clearly disclose", results[0]["content"])
        self.assertEqual(results[0]["metadata"]["category"], "influencer_disclosure")

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_empty_retrieval_results(self, mock_emb_cls, mock_vs_cls):
        """Verifies empty similarity search results are safely handled."""
        mock_vs = MagicMock()
        mock_vs_cls.return_value = mock_vs
        mock_vs.similarity_search.return_value = []

        results = search_policy_rules.invoke({"query": "nonexistent policy topic"})
        self.assertEqual(results, [])

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_provider_401_auth_error_sanitized(self, mock_emb_cls, mock_vs_cls):
        """Verifies 401 Unauthorized errors are caught and sanitized without leaking secrets."""
        mock_vs = MagicMock()
        mock_vs_cls.return_value = mock_vs
        mock_vs.similarity_search.side_effect = Exception("401 Unauthorized: The given API key is invalid")

        results = search_policy_rules.invoke({"query": "disclosure rules"})
        self.assertEqual(results, [])

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_provider_429_rate_limit_sanitized(self, mock_emb_cls, mock_vs_cls):
        """Verifies 429 Rate Limit errors are caught and sanitized."""
        mock_vs = MagicMock()
        mock_vs_cls.return_value = mock_vs
        mock_vs.similarity_search.side_effect = Exception("429 RateLimitError: Search requests per second exceeded")

        results = search_policy_rules.invoke({"query": "disclosure rules"})
        self.assertEqual(results, [])

    @patch("backend.src.graph.tools.AzureSearch")
    @patch("backend.src.graph.tools.AzureOpenAIEmbeddings")
    def test_provider_timeout_sanitized(self, mock_emb_cls, mock_vs_cls):
        """Verifies network timeout errors are caught and sanitized."""
        mock_vs = MagicMock()
        mock_vs_cls.return_value = mock_vs
        mock_vs.similarity_search.side_effect = TimeoutError("Request timed out after 15.0s")

        results = search_policy_rules.invoke({"query": "disclosure rules"})
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
