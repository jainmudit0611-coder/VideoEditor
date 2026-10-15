import os
import time
from dotenv import load_dotenv

load_dotenv(override=True)

from langsmith import Client
from backend.src.graph.workflow import create_graph
from backend.src.graph.state import VideoAuditState

client = Client(
    api_url=os.getenv("LANGCHAIN_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY") if False else os.getenv("LANGCHAIN_API_KEY")
)

project_name = os.getenv("LANGCHAIN_PROJECT", "brand-guardian-video-audit")
print(f"Target LangSmith Project: {project_name}")

initial_state: VideoAuditState = {
    "video_id": "test_langsmith_trace_001",
    "video_path": "scratch/test_frame.jpg",
    "video_metadata": {"title": "Brand Compliance Test Video", "duration_seconds": 10.0},
    "audit_plan": {"checks": [{"area": "influencer endorsement disclosure", "rationale": "Check FTC hashtag"}]},
    "transcript": "Check out this amazing product! Thanks to BrandX for sending this to me.",
    "transcript_items": [{"text": "Check out this amazing product! Thanks to BrandX for sending this to me.", "start_time": 0.0, "end_time": 5.0}],
    "ocr_items": [{"text": "#ad #BrandXPartner", "start_time": 1.0, "end_time": 3.0}],
    "visual_observations": [
        {"timestamp": 1.0, "category": "disclosure", "description": "Text hashtag #ad visible on screen.", "mode": "NATIVE_VISION", "confidence": 0.95}
    ],
    "policy_rules": [],
    "findings": [],
    "iteration_count": 0,
    "max_iterations": 1,
    "final_status": "PENDING",
    "final_report": "",
    "verification_feedback": "",
    "timing_metrics": {},
    "error": None
}

print("Executing LangGraph audit workflow with LangSmith tracing enabled...")
app = create_graph()
t0 = time.time()
output = app.invoke(initial_state)
dur = round(time.time() - t0, 2)
print(f"Workflow completed in {dur}s! Final Status: {output.get('final_status')}")

# Check LangSmith for recent runs
time.sleep(2)  # Allow background telemetry queue flush
print("Querying LangSmith for run traces in project...")
runs = list(client.list_runs(project_name=project_name, limit=3))
print(f"Found {len(runs)} recent runs in '{project_name}':")
for r in runs:
    print(f"  Run ID: {r.id} | Name: {r.name} | Status: {r.status} | Trace: {r.url}")
