"""
Main Execution Entry Point for Brand Guardian AI (Phase 2.5 Hardened Edition).

This module triggers and orchestrates the Hardened Multimodal Agentic Video Compliance Audit Workflow.
Workflow Architecture:
    START → Indexer → Frame Extractor → Audit Planner → Auditor Agent → Verifier Node ──► Router
                                                                                          │
                                                                                      (VERIFIED)
                                                                                          ▼
                                                                                  Report Generator → END
"""

import uuid
import json
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

from backend.src.graph.workflow import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("brand-guardian-runner")

def run_cli_simulation():
    """
    Simulates a Hardened Multimodal Agentic Video Compliance Audit request.
    """
    session_id = str(uuid.uuid4())
    logger.info(f"Starting Hardened Multimodal Agentic Audit Session: {session_id}")

    import sys
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    initial_inputs = {
        "video_url": target_url,
        "video_id": f"vid_{session_id[:8]}",
        "compliance_results": [],
        "errors": [],
        "iteration_count": 0,
        "retrieved_evidence": [],
        "visual_observations": [],
        "transcript_items": [],
        "ocr_items": [],
        "extracted_frame_count": 0,
        "is_degraded_vision_mode": False,
        "timing_metrics": {}
    }

    print("\n=== 1. INITIALIZING HARDENED MULTIMODAL AGENTIC WORKFLOW ===")
    print(f"Input Payload:\n{json.dumps(initial_inputs, indent=2)}")

    try:
        final_state = app.invoke(initial_inputs)
        
        print("\n=== 2. WORKFLOW EXECUTION COMPLETE ===")
        print("\n=== MULTIMODAL COMPLIANCE AUDIT REPORT ===")
        print(f"Video ID:            {final_state.get('video_id')}")
        print(f"Status:              {final_state.get('final_status')}")
        print(f"Vision Execution:    {'DEGRADED (OCR Fallback)' if final_state.get('is_degraded_vision_mode') else 'NATIVE VISION (Azure OpenAI)'}")
        print(f"Iterations Needed:   {final_state.get('iteration_count', 0) + 1}")
        print(f"Frames Analyzed:     {final_state.get('extracted_frame_count', 0)}")
        print(f"Visual Observations: {len(final_state.get('visual_observations', []))}")
        
        timing = final_state.get("timing_metrics", {})
        if timing and isinstance(timing, dict):
            print("\n[ STAGE EXECUTION LATENCIES ]")
            for stage, sec in timing.items():
                print(f"- {stage}: {sec:.2f}s")

        print("\n[ VIOLATIONS DETECTED ]")
        results = final_state.get('compliance_results', [])
        if results:
            for issue in results:
                t_info = f" ({issue.get('timestamp')})" if issue.get('timestamp') else ""
                print(f"- [{issue.get('severity')}] {issue.get('category')}{t_info}: {issue.get('description')}")
        else:
            print("No violations detected.")

        citations = final_state.get('citations', [])
        if citations:
            print("\n[ REGULATORY CITATIONS ]")
            for c in citations:
                print(f"- Document: {c.get('document')} | Rule: {c.get('content')[:80]}...")

        verification = final_state.get('verification_results', {})
        if verification and isinstance(verification, dict):
            print(f"\n[ VERIFIER METRICS ]")
            print(f"Outcome: {verification.get('overall_status')}")
            print(f"Feedback: {verification.get('feedback_summary')}")

        print("\n[ EXECUTIVE SUMMARY REPORT ]")
        print(final_state.get('final_report'))

    except Exception as e:
        logger.error(f"Workflow Execution Failed: {str(e)}")
        raise e

if __name__ == "__main__":
    run_cli_simulation()