import os
import time
from unittest.mock import patch
from dotenv import load_dotenv

load_dotenv(override=True)

from langsmith import Client
from backend.src.graph.workflow import create_graph

project_name = os.getenv("LANGCHAIN_PROJECT", "brand-guardian-video-audit")
client = Client(
    api_url=os.getenv("LANGCHAIN_ENDPOINT"),
    api_key=os.getenv("LANGCHAIN_API_KEY")
)

print(f"Connecting to LangSmith Project: {project_name}")

initial_state = {
    "video_id": "audit_full_flow_001",
    "video_url": "https://www.youtube.com/watch?v=mock_influencer_video",
    "video_metadata": {"title": "Sponsored Tech Review", "duration_seconds": 45.0},
    "iteration_count": 0,
    "max_iterations": 1,
    "final_status": "PENDING",
    "final_report": "",
    "verification_feedback": "",
    "timing_metrics": {},
    "errors": []
}

mock_clean_data = {
    "transcript": "Hey guys! Today we are reviewing this gadget. I want to thank GadgetCorp for sponsoring this video. Use code TECH20 for 20% off!",
    "ocr_text": ["#ad", "#Sponsored", "GadgetCorp Partner"],
    "transcript_items": [
        {"text": "Hey guys! Today we are reviewing this gadget.", "start_time": 0.0, "end_time": 3.0, "speaker": "Creator"},
        {"text": "I want to thank GadgetCorp for sponsoring this video.", "start_time": 3.1, "end_time": 7.0, "speaker": "Creator"},
        {"text": "Use code TECH20 for 20% off!", "start_time": 7.1, "end_time": 10.0, "speaker": "Creator"}
    ],
    "ocr_items": [
        {"text": "#ad", "start_time": 1.0, "end_time": 4.0},
        {"text": "GadgetCorp Partner", "start_time": 3.0, "end_time": 8.0}
    ],
    "video_metadata": {"duration_seconds": 45.0, "fps": 30.0}
}

app = create_graph()

print("\nRunning complete LangGraph audit workflow with live Azure OpenAI and live Azure AI Search RAG...")
t0 = time.time()

# Mock index_video_node internal VI calls so we can trace real planner, auditor, verifier, and reporter
with patch("backend.src.graph.nodes.VideoIndexerService") as mock_vi_cls:
    mock_vi = mock_vi_cls.return_value
    mock_vi.download_youtube_video.return_value = "temp_audit_mock.mp4"
    mock_vi.upload_video.return_value = "vi_mock_123"
    mock_vi.wait_for_processing.return_value = {}
    mock_vi.extract_data.return_value = mock_clean_data
    
    result = app.invoke(initial_state)

dur = round(time.time() - t0, 2)
print(f"\nAudit completed in {dur}s!")
print(f"Final Status: {result.get('final_status')}")
print(f"Audit Plan Checks: {len(result.get('audit_plan', {}).get('checks', []))}")
print(f"Findings Count: {len(result.get('audit_findings', []))}")
print(f"Report Length: {len(result.get('final_report', ''))} characters")
print("\n--- Final Report Excerpt ---")
print(result.get("final_report", "")[:600])

time.sleep(3)
print("\nVerifying live LangSmith trace in project...")
runs = list(client.list_runs(project_name=project_name, limit=6))
print(f"Retrieved {len(runs)} recent runs from LangSmith project '{project_name}':")
for r in runs:
    print(f"  Run ID: {r.id} | Name: {r.name} | Type: {r.run_type} | Status: {r.status}")
