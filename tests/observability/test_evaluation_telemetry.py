import json
import logging
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.src.db.database import Base
from backend.src.db.models import User, UserRole, EvaluationRun, EvaluationRunStatus
from backend.src.db.evaluation_repository import EvaluationRepository
from backend.src.services.evaluation_service import EvaluationService
from backend.src.services.auth_service import AuthService
from backend.src.api.server import app
from backend.src.observability.events import ObservabilityEvent
from backend.src.observability.structured_logger import StructuredJsonFormatter, get_logger
from backend.src.observability.correlation import clear_correlation_context


class TestEvaluationTelemetryAndAdminSummary(unittest.TestCase):
    """
    Tests evaluation framework telemetry emission (run/case lifecycle)
    and protected operator observability summary endpoint.
    """

    def setUp(self):
        clear_correlation_context()
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.client = TestClient(app)

        from backend.src.db.database import get_db

        def override_get_db():
            try:
                yield self.session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setFormatter(StructuredJsonFormatter())

        for name in [
            "brand-guardian-evaluation-service",
            "brand-guardian-evaluation-runner",
        ]:
            l = get_logger(name)
            l.setLevel(logging.INFO)
            l.addHandler(self.handler)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.session.close()
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

    @patch("backend.src.services.evaluation_service.load_evaluation_cases")
    @patch("backend.src.services.evaluation_service.EvaluationSuiteRunner.run_suite")
    def test_evaluation_run_emits_telemetry_lifecycle(self, mock_run_suite, mock_load_cases):
        """Verifies evaluation service emits evaluation_started and evaluation_completed with duration."""
        mock_load_cases.return_value = [MagicMock(case_id="case_001"), MagicMock(case_id="case_002")]
        
        mock_summary = MagicMock()
        mock_summary.n_cases = 2
        mock_summary.error_analysis = []
        mock_summary.case_results = []
        mock_summary.dataset_version = "v1"
        mock_summary.dataset_type = "test"
        mock_summary.execution_modes = ["NATIVE_VISION"]
        mock_summary.limitations = []
        mock_summary.aggregate_metrics = {}
        mock_run_suite.return_value = mock_summary

        run = EvaluationRepository.create_run(
            session=self.session,
            run_name="Telemetry Test Run",
            model_name="gpt-4o",
            model_provider="azure",
            dataset_version="v1"
        )

        service = EvaluationService()
        completed = service.execute_run(session=self.session, run_id=run.id)
        self.assertIsNotNone(completed)

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]

        self.assertIn("evaluation_started", event_names)
        self.assertIn("evaluation_completed", event_names)

        start_event = next(e for e in events if e.get("event") == "evaluation_started")
        self.assertEqual(start_event.get("evaluation_run_id"), run.id)
        self.assertEqual(start_event.get("model_name"), "gpt-4o")

        complete_event = next(e for e in events if e.get("event") == "evaluation_completed")
        self.assertEqual(complete_event.get("evaluation_run_id"), run.id)
        self.assertEqual(complete_event.get("case_count"), 2)
        self.assertIn("duration_ms", complete_event)

    def test_admin_observability_summary_unauthorized_access(self):
        """Verifies GET /api/admin/observability/summary rejects unauthenticated users."""
        response = self.client.get("/api/admin/observability/summary")
        self.assertEqual(response.status_code, 401)

    def test_admin_observability_summary_forbidden_for_normal_user(self):
        """Verifies GET /api/admin/observability/summary rejects normal USER role with 403."""
        from backend.src.api.auth_dependencies import get_current_active_user
        mock_user = MagicMock(id="u1", role=UserRole.USER, is_active=True)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        response = self.client.get("/api/admin/observability/summary")
        self.assertEqual(response.status_code, 403)

    def test_admin_observability_summary_success_for_admin(self):
        """Verifies GET /api/admin/observability/summary succeeds for ADMIN with safe metrics."""
        from backend.src.api.auth_dependencies import get_current_active_user
        mock_admin = MagicMock(id="admin_1", role=UserRole.ADMIN, is_active=True)
        app.dependency_overrides[get_current_active_user] = lambda: mock_admin

        response = self.client.get("/api/admin/observability/summary")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data.get("service"), "brand-guardian-api")
        self.assertIn("app_version", data)
        self.assertIn("database", data)
        self.assertIn("redis", data)
        self.assertIn("audit_jobs", data)
        self.assertIn("total", data["audit_jobs"])


if __name__ == "__main__":
    unittest.main()
