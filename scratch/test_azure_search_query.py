import os
from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
openai_key = os.getenv("AZURE_OPENAI_API_KEY")

from urllib.parse import urlparse
parsed = urlparse(openai_endpoint)
base_endpoint = f"{parsed.scheme}://{parsed.netloc}"

try:
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
        azure_endpoint=base_endpoint,
        api_key=openai_key,
        openai_api_version="2024-02-01",
    )

    vector_store = AzureSearch(
        azure_search_endpoint=endpoint,
        azure_search_key=api_key,
        index_name=index_name,
        embedding_function=embeddings.embed_query
    )

    print("Attempting similarity search on compliance-rules-index...")
    docs = vector_store.similarity_search("FTC disclosures", k=2)
    print("Search returned docs:", len(docs))
except Exception as e:
    print(f"Vector search failed: {type(e).__name__}: {e}")
