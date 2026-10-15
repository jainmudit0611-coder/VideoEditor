import os
from dotenv import load_dotenv

load_dotenv(override=True)

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

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
api_key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index")

client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))

current_idx = client.get_index(index_name)
print(f"Current index '{index_name}' fields:", [f.name for f in current_idx.fields])

# Let's see if we can create_or_update with additional fields
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

new_index_def = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
)

try:
    updated_idx = client.create_or_update_index(new_index_def)
    print(f"Successfully updated index '{index_name}' in-place! Fields now:", [f.name for f in updated_idx.fields])
except Exception as e:
    print(f"Failed to update index in-place: {type(e).__name__}: {e}")
