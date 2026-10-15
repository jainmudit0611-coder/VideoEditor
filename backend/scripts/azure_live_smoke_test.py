"""
Real Azure Integration Smoke Test Suite.
Validates live integration against real cloud resources without exposing secrets.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load active environment
load_dotenv(override=True)

from backend.src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("azure-live-smoke")

def test_live_azure_openai():
    logger.info("--- 1. Testing Live Azure OpenAI ---")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    emb_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    if not endpoint or not api_key:
        logger.warning("Azure OpenAI: SKIPPED (unconfigured)")
        return False

    try:
        from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

        # 1. Chat Completion
        chat = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            azure_deployment=deployment,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            request_timeout=15,
            max_retries=1
        )
        chat_resp = chat.invoke("Ping: respond with 'PONG'")
        logger.info(f"  [PASS] Live Chat Completion: received response (chars={len(chat_resp.content)})")

        # 2. Embeddings
        emb = AzureOpenAIEmbeddings(
            azure_endpoint=endpoint,
            api_key=api_key,
            azure_deployment=emb_deployment,
            openai_api_version="2024-02-01",
            request_timeout=15,
            max_retries=1
        )
        vec = emb.embed_query("Brand Guardian video compliance test")
        logger.info(f"  [PASS] Live Embeddings: generated vector (dim={len(vec)})")
        return True
    except Exception as e:
        logger.error(f"  [FAIL] Live Azure OpenAI failed: {type(e).__name__}: {e}")
        return False

def test_live_vision_analyzer():
    logger.info("--- 2. Testing Live Multimodal Vision Analyzer ---")
    try:
        import numpy as np
        import cv2
        from backend.src.services.vision_analyzer import VisionAnalyzerService

        analyzer = VisionAnalyzerService()
        if not analyzer.is_configured:
            logger.warning("Vision Analyzer: SKIPPED (is_configured=False)")
            return False

        # Create temporary test frame
        test_frame = "scratch/azure_live_test_frame.jpg"
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(test_frame, img)

        obs = analyzer.analyze_frame(test_frame, timestamp=0.5)
        logger.info(f"  [PASS] Live Vision Analyzer: executed successfully (observations={len(obs)})")
        if obs:
            logger.info(f"  [PASS] First observation mode: {obs[0].get('mode')}, category: {obs[0].get('category')}")
        return True
    except Exception as e:
        logger.error(f"  [FAIL] Live Vision Analyzer failed: {type(e).__name__}: {e}")
        return False

def test_live_langsmith():
    logger.info("--- 3. Testing Live LangSmith Tracing ---")
    api_key = os.getenv("LANGCHAIN_API_KEY")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    project = os.getenv("LANGCHAIN_PROJECT", "brand-guardian-video-audit")

    if not api_key:
        logger.warning("LangSmith: SKIPPED (unconfigured)")
        return False

    try:
        from langsmith import Client
        client = Client(api_url=endpoint, api_key=api_key)
        proj = client.read_project(project_name=project)
        logger.info(f"  [PASS] Live LangSmith: connected and validated project '{project}' (id={proj.id})")
        return True
    except Exception as e:
        logger.error(f"  [FAIL] Live LangSmith failed: {type(e).__name__}: {e}")
        return False

def test_live_azure_search():
    logger.info("--- 4. Testing Live Azure AI Search ---")
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index")

    if not endpoint or not api_key:
        logger.warning("Azure AI Search: SKIPPED (unconfigured)")
        return False

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient
        from backend.src.graph.tools import search_policy_rules

        client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
        indexes = [idx.name for idx in client.list_indexes()]
        logger.info(f"  [PASS] Search Service Reachable. Existing indexes: {indexes}")
        if index_name not in indexes:
            logger.warning(f"  [FAIL] Target index '{index_name}' not found.")
            return False

        idx = client.get_index(index_name)
        fields = [f.name for f in idx.fields]
        logger.info(f"  [PASS] Target index '{index_name}' schema fields: {fields}")

        # Real End-to-End Vector Retrieval Verification
        logger.info("  Testing real policy vector retrieval via search_policy_rules...")
        docs = search_policy_rules.invoke({"query": "influencer endorsement disclosure"})
        if not docs:
            logger.warning("  [FAIL] Vector search returned 0 documents.")
            return False

        logger.info(f"  [PASS] Live Vector RAG returned {len(docs)} policy chunks.")
        for d in docs:
            logger.info(f"    - Document: {d.get('document')} | Content: {d.get('content')[:80].replace(chr(10), ' ')}...")

        return True
    except Exception as e:
        logger.error(f"  [FAIL] Live Azure AI Search failed: {type(e).__name__}: {e}")
        return False

def test_live_app_insights() -> bool:
    logger.info("--- 5. Testing Live Application Insights Telemetry ---")
    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_str:
        logger.warning("Application Insights: SKIPPED (unconfigured)")
        return False
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry import trace
        configure_azure_monitor(connection_string=conn_str, logger_name="brand-guardian-smoke-test")
        tracer = trace.get_tracer("brand-guardian-smoke-tracer")
        with tracer.start_as_current_span("smoke-test-span") as span:
            span.set_attribute("smoke.status", "VERIFIED")
        logger.info("  [PASS] Application Insights: telemetry configured and span emitted successfully.")
        return True
    except Exception as e:
        logger.error(f"  [FAIL] Live Application Insights failed: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    results = {
        "azure_openai": test_live_azure_openai(),
        "vision_analyzer": test_live_vision_analyzer(),
        "langsmith": test_live_langsmith(),
        "azure_search": test_live_azure_search(),
        "app_insights": test_live_app_insights()
    }
    logger.info(f"Live Smoke Test Summary: {results}")
