import os
from dotenv import load_dotenv

load_dotenv(override=True)

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

from langchain_openai import AzureChatOpenAI

print("Testing AzureChatOpenAI with full endpoint as in .env:")
try:
    chat1 = AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=deployment,
        api_version=api_version,
        request_timeout=15,
        max_retries=1
    )
    res1 = chat1.invoke("Hello")
    print("Full endpoint SUCCESS! Response:", res1.content)
except Exception as e:
    print(f"Full endpoint FAILED: {type(e).__name__}: {e}")

from urllib.parse import urlparse
parsed = urlparse(endpoint)
base_endpoint = f"{parsed.scheme}://{parsed.netloc}"

print("\nTesting AzureChatOpenAI with base endpoint:")
try:
    chat2 = AzureChatOpenAI(
        azure_endpoint=base_endpoint,
        api_key=api_key,
        azure_deployment=deployment,
        api_version=api_version,
        request_timeout=15,
        max_retries=1
    )
    res2 = chat2.invoke("Hello")
    print("Base endpoint SUCCESS! Response:", res2.content)
except Exception as e:
    print(f"Base endpoint FAILED: {type(e).__name__}: {e}")
