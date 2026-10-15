"""
Brand Guardian AI — Regulatory Compliance Policy Indexer.
Reads compliance guidelines from backend/data, generates dense embeddings,
and idempotently indexes chunks into Azure AI Search.
"""
import os
import glob
import hashlib
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("brand-guardian-indexer")


def ensure_index_schema(endpoint: str, api_key: str, index_name: str) -> None:
    """
    Ensures Azure AI Search index exists and contains all required vector fields.
    Updates the index in-place without deleting existing data.
    """
    client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
    
    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="myHnswProfile",
        ),
        SearchField(name="metadata", type=SearchFieldDataType.String, searchable=True),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")],
    )

    index_def = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
    )

    client.create_or_update_index(index_def)
    logger.info(f"Verified and updated Azure Search index schema for '{index_name}'.")


def get_normalized_openai_endpoint() -> str:
    """Extracts base host scheme://netloc for Azure OpenAI to prevent /v1 path conflicts."""
    raw_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    parsed = urlparse(raw_endpoint)
    if parsed.netloc and parsed.path and parsed.path != "/":
        return f"{parsed.scheme}://{parsed.netloc}"
    return raw_endpoint


def index_compliance_documents() -> int:
    """
    Repeatable, idempotent indexing of regulatory policy PDFs.
    Returns the total number of indexed document chunks.
    """
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index")

    openai_endpoint = get_normalized_openai_endpoint()
    openai_key = os.getenv("AZURE_OPENAI_API_KEY")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    if not search_endpoint or not search_key or not openai_endpoint or not openai_key:
        logger.error("Missing required Azure credentials in environment. Aborting indexing.")
        return 0

    # 1. Ensure Index Schema
    try:
        ensure_index_schema(search_endpoint, search_key, index_name)
    except Exception as e:
        logger.error(f"Failed to ensure index schema: {type(e).__name__}: {e}")
        return 0

    # 2. Locate Source PDFs
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.abspath(os.path.join(current_dir, "../data"))
    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))

    if not pdf_files:
        logger.warning(f"No compliance PDFs found in {data_folder}.")
        return 0

    logger.info(f"Discovered {len(pdf_files)} compliance documents to index: {[os.path.basename(p) for p in pdf_files]}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    all_splits = []
    all_ids = []

    # 3. Load & Chunk Documents with Deterministic IDs
    for pdf_path in pdf_files:
        file_name = os.path.basename(pdf_path)
        base_id_prefix = hashlib.md5(file_name.encode("utf-8")).hexdigest()[:8]
        logger.info(f"Processing '{file_name}'...")

        try:
            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()
            splits = text_splitter.split_documents(raw_docs)

            category = "influencer_disclosure" if "influencer" in file_name.lower() else "ad_guidelines"

            for i, split in enumerate(splits):
                chunk_id = f"{base_id_prefix}-{i:04d}"
                split.metadata["source"] = file_name
                split.metadata["category"] = category
                split.metadata["chunk_index"] = i
                split.metadata["total_chunks"] = len(splits)

                all_splits.append(split)
                all_ids.append(chunk_id)

            logger.info(f" -> '{file_name}': generated {len(splits)} chunks.")
        except Exception as e:
            logger.error(f"Failed to process '{file_name}': {type(e).__name__}: {e}")

    if not all_splits:
        logger.warning("No valid text chunks were extracted from documents.")
        return 0

    # 4. Initialize Embeddings & Vector Store
    try:
        logger.info("Initializing Azure OpenAI Embeddings...")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=embedding_deployment,
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            request_timeout=30.0,
            max_retries=2
        )

        vector_store = AzureSearch(
            azure_search_endpoint=search_endpoint,
            azure_search_key=search_key,
            index_name=index_name,
            embedding_function=embeddings.embed_query
        )

        # 5. Idempotent Upsert (using deterministic chunk IDs)
        logger.info(f"Uploading {len(all_splits)} chunks to Azure AI Search index '{index_name}'...")
        vector_store.add_documents(documents=all_splits, ids=all_ids)
        logger.info(f"Successfully uploaded {len(all_splits)} compliance rule chunks.")

        # 6. Verification Retrieval Test
        logger.info("Running verification similarity search for 'influencer endorsement disclosure'...")
        test_results = vector_store.similarity_search("influencer endorsement disclosure", k=2)
        logger.info(f"Verification query returned {len(test_results)} document chunks:")
        for doc in test_results:
            source = doc.metadata.get("source", "unknown")
            snippet = doc.page_content[:120].replace("\n", " ")
            logger.info(f"  [VERIFIED] Source: {source} | Snippet: {snippet}...")

        return len(all_splits)
    except Exception as e:
        logger.error(f"Failed to complete indexing or verification: {type(e).__name__}: {e}")
        return 0


if __name__ == "__main__":
    count = index_compliance_documents()
    print(f"\nIndexing finished. Total chunks indexed: {count}")