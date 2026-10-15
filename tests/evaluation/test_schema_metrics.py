import unittest
from backend.evaluation.metrics.schema_metrics import evaluate_schema

class TestSchemaMetrics(unittest.TestCase):
    """Deterministic unit tests for audit output schema validation."""

    def test_valid_audit_result_schema(self):
        output = {
            "status": "PASS",
            "final_report": "Audit report summary.",
            "compliance_results": [
                {"category": "FTC_DISCLOSURE", "severity": "PASS", "description": "OK"}
            ],
            "citations": [],
            "verification_summary": {"status": "VERIFIED"}
        }
        res = evaluate_schema(output)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.schema_validity_rate, 1.0)
        self.assertEqual(len(res.missing_required_fields), 0)
        self.assertEqual(len(res.validation_errors), 0)

    def test_missing_required_field(self):
        output = {
            # missing "status" and "final_report"
            "compliance_results": []
        }
        res = evaluate_schema(output)
        self.assertFalse(res.is_valid)
        self.assertLess(res.schema_validity_rate, 1.0)
        self.assertIn("status", res.missing_required_fields)

    def test_invalid_status_enum(self):
        output = {
            "status": "MAYBE_COMPLIANT",  # Invalid enum
            "compliance_results": []
        }
        res = evaluate_schema(output)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Invalid status" in err for err in res.validation_errors))

    def test_invalid_compliance_results_type(self):
        output = {
            "status": "PASS",
            "compliance_results": "should_be_a_list_not_a_string"
        }
        res = evaluate_schema(output)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("compliance_results" in err for err in res.invalid_data_types))

if __name__ == "__main__":
    unittest.main()
