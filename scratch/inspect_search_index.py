import os
from dotenv import load_dotenv

load_dotenv(override=True)

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index")

client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
idx = client.get_index(index_name)

print("Index name:", idx.name)
print("Fields:")
for f in idx.fields:
    print(f"  Field: {f.name}, type: {f.type}, searchable: {getattr(f, 'searchable', None)}, retrievable: {getattr(f, 'hidden', None)}")

# Check document count
search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(api_key))
doc_count = search_client.get_document_count()
print("Document count:", doc_count)
