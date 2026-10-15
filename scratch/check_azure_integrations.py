import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load from .env
load_dotenv(override=True)

from backend.src.config import settings

def mask(val: str | None) -> str:
    if not val:
        return "<EMPTY>"
    if len(val) <= 8:
        return "***"
    return f"{val[:4]}...{val[-4:]} (len={len(val)})"

def test_settings_validation():
    print("\n--- 1. Settings Environment Validation ---")
    val = settings.validate_environment()
    for k, v in val.items():
        print(f"  {k}: {v}")

def test_azure_search():
    print("\n--- 2. Azure AI Search Check ---")
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index")

    print(f"  Endpoint: {endpoint}")
    print(f"  API Key configured: {bool(api_key)}")
    print(f"  Target Index: {index_name}")

    if not endpoint or not api_key:
        print("  Status: BLOCKED_BY_CREDENTIALS (missing endpoint or key)")
        return

    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient

        client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
        indexes = list(client.list_indexes())
        index_names = [idx.name for idx in indexes]
        print(f"  Connected successfully! Existing indexes: {index_names}")
        if index_name in index_names:
            print(f"  Index '{index_name}' EXISTS.")
            idx = client.get_index(index_name)
            fields = [f.name for f in idx.fields]
            print(f"  Fields in '{index_name}': {fields}")
        else:
            print(f"  Index '{index_name}' DOES NOT EXIST in this search service.")
    except Exception as e:
        print(f"  Search check failed: {type(e).__name__}: {str(e)[:150]}")

def test_azure_openai():
    print("\n--- 3. Azure OpenAI Check ---")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    emb_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    print(f"  Endpoint: {endpoint}")
    print(f"  API Key configured: {bool(api_key)}")
    print(f"  Chat Deployment: {chat_deployment}")
    print(f"  Embedding Deployment: {emb_deployment}")
    print(f"  API Version: {api_version}")

    if not endpoint or not api_key:
        print("  Status: BLOCKED_BY_CREDENTIALS")
        return

    # Let's test standard HTTP request to deployments endpoint or chat completion
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    
    # Check root host
    from urllib.parse import urlparse
    parsed = urlparse(endpoint)
    base_endpoint = f"{parsed.scheme}://{parsed.netloc}"
    print(f"  Base host: {base_endpoint}")

    # Test 1: Direct endpoint as configured
    try:
        url = f"{endpoint.rstrip('/')}/openai/deployments?api-version={api_version}"
        res = requests.get(url, headers=headers, timeout=10)
        print(f"  GET {url} -> Status {res.status_code}")
        if res.status_code == 200:
            deps = [d.get("id") for d in res.json().get("data", [])]
            print(f"  Available deployments: {deps}")
        else:
            print(f"  Response: {res.text[:200]}")
    except Exception as e:
        print(f"  Direct endpoint request failed: {type(e).__name__}: {str(e)[:150]}")

    # Test 2: Base host if endpoint had path
    if parsed.path and parsed.path != "/":
        try:
            url2 = f"{base_endpoint}/openai/deployments?api-version={api_version}"
            res2 = requests.get(url2, headers=headers, timeout=10)
            print(f"  GET {url2} -> Status {res2.status_code}")
            if res2.status_code == 200:
                deps = [d.get("id") for d in res2.json().get("data", [])]
                print(f"  Available deployments on base host: {deps}")
            else:
                print(f"  Response on base host: {res2.text[:200]}")
        except Exception as e:
            print(f"  Base endpoint request failed: {type(e).__name__}: {str(e)[:150]}")

    # Test 3: LangChain AzureChatOpenAI invocation if deployment is known
    if chat_deployment:
        try:
            from langchain_openai import AzureChatOpenAI
            chat = AzureChatOpenAI(
                azure_endpoint=base_endpoint,
                api_key=api_key,
                azure_deployment=chat_deployment,
                api_version=api_version,
                request_timeout=15,
                max_retries=1
            )
            response = chat.invoke("Say 'ready'")
            print(f"  AzureChatOpenAI response: {response.content}")
        except Exception as e:
            print(f"  AzureChatOpenAI test failed: {type(e).__name__}: {str(e)[:150]}")

    # Test 4: LangChain AzureOpenAIEmbeddings invocation if deployment is known
    if emb_deployment:
        try:
            from langchain_openai import AzureOpenAIEmbeddings
            emb = AzureOpenAIEmbeddings(
                azure_endpoint=base_endpoint,
                api_key=api_key,
                azure_deployment=emb_deployment,
                openai_api_version="2024-02-01",
                request_timeout=15,
                max_retries=1
            )
            vec = emb.embed_query("compliance policy test")
            print(f"  AzureOpenAIEmbeddings success! Vector dimension: {len(vec)}")
        except Exception as e:
            print(f"  AzureOpenAIEmbeddings test failed: {type(e).__name__}: {str(e)[:150]}")

def test_azure_storage():
    print("\n--- 4. Azure Storage Check ---")
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    print(f"  Connection string configured: {bool(conn_str)}")
    if not conn_str:
        print("  Status: BLOCKED_BY_CREDENTIALS")
        return

    try:
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(conn_str)
        containers = list(client.list_containers())
        print(f"  Connected to Storage! Containers: {[c.name for c in containers]}")
    except Exception as e:
        print(f"  Storage test failed: {type(e).__name__}: {str(e)[:150]}")

def test_azure_video_indexer():
    print("\n--- 5. Azure Video Indexer Check ---")
    account_id = os.getenv("AZURE_VI_ACCOUNT_ID")
    location = os.getenv("AZURE_VI_LOCATION")
    sub_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    rg = os.getenv("AZURE_RESOURCE_GROUP")
    vi_name = os.getenv("AZURE_VI_NAME")

    print(f"  Account ID: {account_id}")
    print(f"  Location: {location}")
    print(f"  Subscription ID: {sub_id}")
    print(f"  Resource Group: {rg}")
    print(f"  VI Name: {vi_name}")

    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        token = cred.get_token("https://management.azure.com/.default")
        print("  ARM Token acquired successfully via DefaultAzureCredential!")
    except Exception as e:
        print(f"  DefaultAzureCredential ARM Token acquisition failed: {type(e).__name__}: {str(e)[:150]}")

def test_application_insights():
    print("\n--- 6. Azure Application Insights Check ---")
    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    print(f"  Configured: {bool(conn_str)}")
    if not conn_str:
        print("  Status: BLOCKED_BY_CREDENTIALS")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        # Test configuring without crashing
        print(f"  Connection string format: starts with '{conn_str[:15]}...'")
    except Exception as e:
        print(f"  App Insights check failed: {type(e).__name__}: {str(e)[:150]}")

def test_langsmith():
    print("\n--- 7. LangSmith Tracing Check ---")
    api_key = os.getenv("LANGCHAIN_API_KEY")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    project = os.getenv("LANGCHAIN_PROJECT", "brand-guardian-video-audit")
    tracing = os.getenv("LANGCHAIN_TRACING_V2")

    print(f"  Tracing Enabled: {tracing}")
    print(f"  Endpoint: {endpoint}")
    print(f"  Project: {project}")
    print(f"  API Key configured: {bool(api_key)}")

    if not api_key:
        print("  Status: BLOCKED_BY_CREDENTIALS")
        return

    try:
        from langsmith import Client
        client = Client(api_url=endpoint, api_key=api_key)
        # Test reading projects
        projects = list(client.list_projects(limit=3))
        print(f"  LangSmith connection SUCCESS! Projects accessible: {[p.name for p in projects]}")
    except Exception as e:
        print(f"  LangSmith test failed: {type(e).__name__}: {str(e)[:150]}")

if __name__ == "__main__":
    test_settings_validation()
    test_azure_search()
    test_azure_openai()
    test_azure_storage()
    test_azure_video_indexer()
    test_application_insights()
    test_langsmith()
