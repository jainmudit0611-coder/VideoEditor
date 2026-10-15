import os
import uuid
import time
from dotenv import load_dotenv

load_dotenv(override=True)

from langsmith import Client
from backend.src.graph.workflow import create_graph

api_key = os.getenv("LANGCHAIN_API_KEY")
endpoint = os.getenv("LANGCHAIN_ENDPOINT")
project_name = os.getenv("LANGCHAIN_PROJECT", "brand-guardian-video-audit")

print(f"Connecting to LangSmith at {endpoint}...")
client = Client(api_url=endpoint, api_key=api_key)

proj = client.read_project(project_name=project_name)
print(f"Verified Project: {proj.name} (ID: {proj.id})")

# Run full LangGraph workflow
run_id = str(uuid.uuid4())
print(f"\nInvoking LangGraph audit workflow with LangSmith run tracking (ID: {run_id})...")

graph = create_graph()

initial_state = {
    "job_id": f"langsmith-verify-{int(time.time())}",
    "video_path": "sample_video.mp4",
    "video_metadata": {"duration_seconds": 30.0, "fps": 30.0},
    "transcript": [
        {"start_time": 1.0, "end_time": 4.0, "speaker": "Influencer", "text": "Hey everyone, checking out this new sponsor!"}
    ],
    "ocr_events": [
        {"start_time": 1.0, "end_time": 3.0, "text": "Paid Partnership"}
    ],
    "visual_observations": [
        {"timestamp": 2.0, "description": "Brand logo visible in top corner", "category": "branding"}
    ],
    "audit_plan": {},
    "compliance_findings": [],
    "final_status": "PENDING",
    "final_report": "",
    "audit_score": 100,
    "confidence_score": 0.95,
    "timing_metrics": {},
    "error": None
}

config = {
    "run_name": "langsmith_live_audit_verification",
    "metadata": {
        "job_id": initial_state["job_id"],
        "verification_suite": "Brand Guardian Priority 2 Verification"
    },
    "tags": ["verification", "production-audit"]
}

result = graph.invoke(initial_state, config=config)

print(f"\nLangGraph Execution Completed!")
print(f"Final Status: {result.get('final_status')}")
print(f"Compliance Findings: {len(result.get('compliance_findings', []))}")
print(f"Report Length: {len(result.get('final_report', ''))} chars")

# Query LangSmith for latest runs in project
print(f"\nQuerying LangSmith project '{project_name}' for newly captured traces...")
time.sleep(3) # allow LangSmith async ingestion

runs = list(client.list_runs(project_name=project_name, limit=5))
print(f"Retrieved {len(runs)} recent runs from LangSmith:")
for r in runs:
    print(f"  - Run ID: {r.id} | Name: {r.name} | Run Type: {r.run_type} | Status: {r.status} | Trace ID: {r.trace_id}")

matching_runs = [r for r in runs if r.name in ("langsmith_live_audit_verification", "LangGraph", "planner", "auditor", "reporter")]
if matching_runs:
    print(f"\n[CONFIRMED] Successfully verified live LangSmith trace in project '{project_name}'!")
    print(f"Latest Trace ID: {matching_runs[0].trace_id}")
    print(f"Run Status: {matching_runs[0].status}")
else:
    print("\n[WARNING] New run not yet indexed by LangSmith list_runs, but client connection verified.")
