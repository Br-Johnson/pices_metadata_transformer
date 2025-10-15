import unittest

from scripts.dto import build_canonical_dto
from scripts.matching.engine import MatchCandidate, MatchingEngine


class MatchingEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = build_canonical_dto(
            source_path="FGDC/test.xml",
            zenodo_metadata={
                "title": "Ocean Temperature Dataset",
                "description": "Observations collected during the 2020 campaign.",
                "creators": [{"name": "Jane Doe"}, {"name": "John Smith"}],
            },
        )
        self.engine = MatchingEngine(acceptance_threshold=0.5)

    def test_scores_confident_match(self) -> None:
        candidate = MatchCandidate(
            source="datacite",
            identifier="https://doi.org/10.1234/test",
            title="Ocean Temperature Dataset",
            creators=["Jane Doe", "John Smith"],
            abstract="Observations collected during the 2020 campaign",
        )
        results = self.engine.score_candidates(self.record, [candidate])
        self.assertEqual(len(results), 1)
        self.assertGreaterEqual(results[0].score, 0.5)

    def test_filter_confident(self) -> None:
        candidate = MatchCandidate(
            source="crossref",
            identifier="https://doi.org/10.5678/test",
            title="Ocean Data",
            creators=["Jane Doe"],
            abstract="Summary",
        )
        results = self.engine.score_candidates(self.record, [candidate])
        confident = self.engine.filter_confident(results)
        self.assertLessEqual(len(confident), len(results))


if __name__ == "__main__":
    unittest.main()

