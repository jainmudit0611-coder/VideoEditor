import unittest
from backend.evaluation.schemas import ExpectedCitation
from backend.evaluation.metrics.citation_metrics import evaluate_citations

class TestCitationMetrics(unittest.TestCase):
    """Deterministic unit tests for policy/RAG citation metrics."""

    def test_complete_citation_presence(self):
        expected = [
            ExpectedCitation(rule_category="FTC_DISCLOSURE", document_contains="FTC Guides")
        ]
        actual_citations = [
            {
                "rule_category": "FTC_DISCLOSURE",
                "document": "FTC Guides Concerning Use of Endorsements",
                "content": "Disclosures must be clear and conspicuous."
            }
        ]
        actual_findings = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL"}
        ]
        res = evaluate_citations(expected, actual_citations, actual_findings)

        self.assertEqual(res.total_findings, 1)
        self.assertEqual(res.cited_findings, 1)
        self.assertEqual(res.citation_presence_rate, 1.0)
        self.assertEqual(res.complete_citations_count, 1)
        self.assertEqual(res.completeness_rate, 1.0)

    def test_missing_citation(self):
        expected = [
            ExpectedCitation(rule_category="FTC_DISCLOSURE")
        ]
        actual_citations = []
        actual_findings = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL"}
        ]
        res = evaluate_citations(expected, actual_citations, actual_findings)

        self.assertEqual(res.total_findings, 1)
        self.assertEqual(res.cited_findings, 0)
        self.assertEqual(res.citation_presence_rate, 0.0)
        self.assertEqual(res.completeness_rate, 0.0)

    def test_incomplete_citation_missing_content(self):
        expected = []
        actual_citations = [
            {
                "rule_category": "FTC_DISCLOSURE",
                "document": "FTC Guides",
                "content": ""  # empty content
            }
        ]
        actual_findings = [
            {"category": "FTC_DISCLOSURE", "severity": "FAIL"}
        ]
        res = evaluate_citations(expected, actual_citations, actual_findings)

        self.assertEqual(res.cited_findings, 1)
        self.assertEqual(res.complete_citations_count, 0)
        self.assertEqual(res.completeness_rate, 0.0)

if __name__ == "__main__":
    unittest.main()
