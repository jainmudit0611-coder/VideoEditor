"""
Agentic Multimodal Workflow Definition for Brand Guardian AI.

This module defines the StateGraph orchestrating the video compliance audit.
Includes Video Indexer, Frame Extraction & Vision Analysis, Audit Planner,
Auditor Agent, Verifier Node, and Bounded Conditional Edge Router.

Architecture:
    [START] -> [indexer] -> [frame_extractor] -> [planner] -> [auditor] -> [verifier]
                                                                  ^              │
                                                                  │  NEEDS_MORE  │
                                                                  └── EVIDENCE ──┤ (iteration < MAX_AUDIT_ITERATIONS)
                                                                                 │
                                                                             VERIFIED / UNRESOLVED
                                                                                 ▼
                                                                       [report_generator] -> [END]
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

# Import State Schema
from backend.src.graph.state import VideoAuditState

# Import Functional Nodes
from backend.src.graph.nodes import (
    index_video_node,
    extract_multimodal_frames_node,
    plan_audit_node,
    audit_content_node,
    verify_findings_node,
    generate_report_node
)

from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
)

logger = get_logger("brand-guardian-workflow")

# Safety upper bound for agent reflection loop iterations
MAX_AUDIT_ITERATIONS = 2

def route_after_verification(state: VideoAuditState) -> Literal["report_generator", "auditor"]:
    """
    Conditional router function evaluating verification outcome and iteration limit.
    """
    verification = state.get("verification_results", {})
    overall_status = verification.get("overall_status", "VERIFIED") if isinstance(verification, dict) else "VERIFIED"
    iteration_count = state.get("iteration_count", 0)
    
    logger.info(f"Router Check: status='{overall_status}', iteration={iteration_count}/{MAX_AUDIT_ITERATIONS}")

    log_event(
        logger,
        ObservabilityEvent.VERIFIER_COMPLETED,
        message=f"Verifier completed check: outcome={overall_status}, iteration={iteration_count}",
        overall_status=overall_status,
        iteration=iteration_count
    )

    if overall_status == "NEEDS_MORE_EVIDENCE" and iteration_count < MAX_AUDIT_ITERATIONS:
        log_event(
            logger,
            ObservabilityEvent.AUDIT_ITERATION_REQUESTED,
            message=f"Routing back to Auditor Node for evidence refinement (iteration {iteration_count + 1})",
            iteration=iteration_count + 1,
            max_iterations=MAX_AUDIT_ITERATIONS
        )
        state["iteration_count"] = iteration_count + 1
        return "auditor"
    
    if iteration_count >= MAX_AUDIT_ITERATIONS and overall_status == "NEEDS_MORE_EVIDENCE":
        log_event(
            logger,
            ObservabilityEvent.AUDIT_ITERATION_LIMIT_REACHED,
            level=logging.WARNING,
            message=f"Reached MAX_AUDIT_ITERATIONS ({MAX_AUDIT_ITERATIONS}). Transitioning to Report Generator with UNRESOLVED status.",
            iteration=iteration_count,
            max_iterations=MAX_AUDIT_ITERATIONS
        )
        state["final_status"] = "UNRESOLVED"

    log_event(
        logger,
        ObservabilityEvent.AUDIT_ROUTED_TO_REPORT,
        message="Routing to Report Generator Node.",
        final_verification_status=overall_status,
        iterations_completed=iteration_count
    )
    return "report_generator"

def create_graph():
    """
    Constructs and compiles the Multimodal Agentic LangGraph workflow.

    Returns:
        CompiledGraph: A runnable graph object ready for execution.
    """
    # 1. Initialize StateGraph with VideoAuditState Schema
    workflow = StateGraph(VideoAuditState)

    # 2. Add Functional Worker Nodes
    workflow.add_node("indexer", index_video_node)
    workflow.add_node("frame_extractor", extract_multimodal_frames_node)
    workflow.add_node("planner", plan_audit_node)
    workflow.add_node("auditor", audit_content_node)
    workflow.add_node("verifier", verify_findings_node)
    workflow.add_node("report_generator", generate_report_node)

    # 3. Define Entry Point and Sequential Transitions
    workflow.set_entry_point("indexer")
    workflow.add_edge("indexer", "frame_extractor")
    workflow.add_edge("frame_extractor", "planner")
    workflow.add_edge("planner", "auditor")
    workflow.add_edge("auditor", "verifier")

    # 4. Add Bounded Conditional Edge Routing after Verifier Node
    workflow.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "auditor": "auditor",
            "report_generator": "report_generator"
        }
    )

    # 5. Connect Report Generator to Termination Node
    workflow.add_edge("report_generator", END)

    # 6. Compile the Graph
    app = workflow.compile()
    return app

# Expose compiled runnable graph
app = create_graph()