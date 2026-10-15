import inspect
from langchain_community.vectorstores.azuresearch import AzureSearch

print("AzureSearch constructor args:")
print(inspect.signature(AzureSearch.__init__))
