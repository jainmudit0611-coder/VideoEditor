import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("LANGCHAIN_API_KEY")
endpoint = os.getenv("LANGCHAIN_ENDPOINT")

from langsmith import Client
client = Client(api_url=endpoint, api_key=api_key)

# Test project access or creation
project_name = "brand-guardian-video-audit"
try:
    proj = client.read_project(project_name=project_name)
    print(f"Project '{project_name}' exists: ID={proj.id}")
except Exception as e:
    print(f"Project '{project_name}' not found or error: {e}")
    try:
        new_proj = client.create_project(project_name=project_name)
        print(f"Created project '{project_name}': ID={new_proj.id}")
    except Exception as e2:
        print(f"Failed to create project: {e2}")
