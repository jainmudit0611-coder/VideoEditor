from langchain_community.vectorstores.azuresearch import AzureSearch

def dummy_embed(text):
    return [0.0] * 1536

vs = AzureSearch(
    azure_search_endpoint="https://video-audit-search-2026.search.windows.net",
    azure_search_key="dummy",
    index_name="dummy-index",
    embedding_function=dummy_embed
)

print("Default fields defined by AzureSearch:")
for f in vs.fields:
    print(f"  Field name: {f.name}, type: {f.type}, key: {getattr(f, 'key', False)}")
