import json
import logging
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from backend.src.graph.workflow import route_after_verification, MAX_AUDIT_ITERATIONS
from backend.src.graph.nodes import (
    plan_audit_node,
    verify_findings_node,
    extract_multimodal_frames_node,
    generate_report_node,
)
from backend.src.graph.tools import (
    search_transcript_evidence,
    search_ocr_evidence,
    check_rule_compliance,
    search_visual_evidence,
)
from backend.src.observability.events import ObservabilityEvent
from backend.src.observability.structured_logger import StructuredJsonFormatter, get_logger
from backend.src.observability.correlation import clear_correlation_context


class TestLangGraphTelemetry(unittest.TestCase):
    """
    Tests agent observability, node execution events, tool call metadata,
    verifier iteration telemetry, and degraded mode observability.
    """

    def setUp(self):
        clear_correlation_context()
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setFormatter(StructuredJsonFormatter())

        for name in [
            "brand-guardian-workflow",
            "brand-guardian-nodes",
            "brand-guardian-tools",
        ]:
            l = get_logger(name)
            l.setLevel(logging.INFO)
            l.addHandler(self.handler)

    def tearDown(self):
        clear_correlation_context()

    def _get_logged_events(self):
        output = self.log_stream.getvalue().strip()
        events = []
        for line in output.split("\n"):
            if line.strip():
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
        return events

    def test_workflow_router_emits_verifier_and_routing_events(self):
        """Verifies router logs verifier outcome and routing decisions."""
        # Case 1: VERIFIED -> report_generator
        state_verified = {
            "verification_results": {"overall_status": "VERIFIED"},
            "iteration_count": 0,
        }
        dest = route_after_verification(state_verified)
        self.assertEqual(dest, "report_generator")

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]
        self.assertIn("verifier_completed", event_names)
        self.assertIn("audit_routed_to_report", event_names)

    def test_workflow_router_iteration_requested_event(self):
        """Verifies router emits audit_iteration_requested when needing more evidence."""
        self.log_stream.truncate(0)
        self.log_stream.seek(0)

        state_needs_more = {
            "verification_results": {"overall_status": "NEEDS_MORE_EVIDENCE"},
            "iteration_count": 0,
        }
        dest = route_after_verification(state_needs_more)
        self.assertEqual(dest, "auditor")
        self.assertEqual(state_needs_more["iteration_count"], 1)

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]
        self.assertIn("verifier_completed", event_names)
        self.assertIn("audit_iteration_requested", event_names)

    def test_workflow_router_max_iteration_limit_reached(self):
        """Verifies router emits audit_iteration_limit_reached when upper bound hit."""
        self.log_stream.truncate(0)
        self.log_stream.seek(0)

        state_max = {
            "verification_results": {"overall_status": "NEEDS_MORE_EVIDENCE"},
            "iteration_count": MAX_AUDIT_ITERATIONS,
        }
        dest = route_after_verification(state_max)
        self.assertEqual(dest, "report_generator")
        self.assertEqual(state_max.get("final_status"), "UNRESOLVED")

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]
        self.assertIn("audit_iteration_limit_reached", event_names)

    def test_degraded_mode_observability(self):
        """Verifies frame extraction emits audit_degraded_mode when OCR fallback is used."""
        # Calling extract_multimodal_frames_node with non-existent file triggers degraded mode
        state = {
            "local_file_path": None,
            "transcript_items": [],
            "ocr_items": [{"text": "ad link in bio", "start_time": 2.0}],
            "timing_metrics": {},
        }
        res = extract_multimodal_frames_node(state)
        self.assertTrue(res["is_degraded_vision_mode"])

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]
        self.assertIn("node_started", event_names)
        self.assertIn("audit_degraded_mode", event_names)
        self.assertIn("node_completed", event_names)

        degraded_event = next(e for e in events if e.get("event") == "audit_degraded_mode")
        self.assertEqual(degraded_event.get("mode"), "DEGRADED_OCR_FALLBACK")

    def test_tools_emit_started_and_completed_with_counts(self):
        """Verifies tools emit agent_tool_started and agent_tool_completed with result counts."""
        self.log_stream.truncate(0)
        self.log_stream.seek(0)

        transcript = "Hello viewers. This video is sponsored by BrandX. Use code SAVE20 for discount."
        results = search_transcript_evidence.invoke({
            "query": "sponsored brand code",
            "transcript_text": transcript
        })
        self.assertTrue(len(results) > 0)

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]

        self.assertIn("agent_tool_started", event_names)
        self.assertIn("agent_tool_completed", event_names)

        complete_event = next(e for e in events if e.get("event") == "agent_tool_completed")
        self.assertEqual(complete_event.get("tool_name"), "search_transcript_evidence")
        self.assertEqual(complete_event.get("result_count"), len(results))
        self.assertIn("duration_ms", complete_event)

    def test_report_generator_node_observability(self):
        """Verifies generate_report_node emits node lifecycle events."""
        self.log_stream.truncate(0)
        self.log_stream.seek(0)

        state = {
            "video_id": "test_vid_123",
            "final_status": "PASS",
            "audit_findings": [],
            "citations": [],
            "verification_results": {"overall_status": "VERIFIED"},
            "timing_metrics": {"verifier_time": 0.05}
        }
        out = generate_report_node(state)
        self.assertIn("final_report", out)

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]
        self.assertIn("node_started", event_names)
        self.assertIn("node_completed", event_names)


if __name__ == "__main__":
    unittest.main()
