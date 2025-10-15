import unittest

from scripts.dto import (
    Attachment,
    BibliographicLink,
    CanonicalRecordDTO,
    build_canonical_dto,
    merge_related_identifiers,
)


class CanonicalDTOTests(unittest.TestCase):
    def test_publisher_is_normalised(self) -> None:
        metadata = {
            "title": "Sample",
            "publisher": "Legacy Publisher",
        }
        dto = build_canonical_dto(
            source_path="FGDC/sample.xml",
            zenodo_metadata=metadata,
        )
        self.assertEqual(
            dto.zenodo_metadata["publisher"],
            CanonicalRecordDTO.PICES_PUBLISHER,
        )
        self.assertEqual(
            dto.zenodo_metadata["imprint_publisher"],
            "Legacy Publisher",
        )

    def test_related_identifiers_merge_without_duplicates(self) -> None:
        metadata = {"title": "Sample", "related_identifiers": []}
        link = BibliographicLink(
            source="datacite",
            identifier="https://doi.org/10.1234/example",
            relation="isAlternativeIdentifierOf",
            confidence=0.91,
            scheme="doi",
        )
        dto = build_canonical_dto(
            source_path="FGDC/sample.xml",
            zenodo_metadata=metadata,
            bibliographic_links=[link],
        )
        merge_related_identifiers(metadata, dto.related_identifiers)
        merge_related_identifiers(metadata, dto.related_identifiers)
        self.assertEqual(len(metadata["related_identifiers"]), 1)
        self.assertEqual(
            metadata["related_identifiers"][0]["identifier"],
            "https://doi.org/10.1234/example",
        )

    def test_attachment_conversion(self) -> None:
        dto = build_canonical_dto(
            source_path="/tmp/FGDC-1.xml",
            zenodo_metadata={"title": "Test"},
            attachments=[
                {
                    "path": "/tmp/file.xml",
                    "description": "Original FGDC metadata XML",
                    "type": "fgdc_xml",
                }
            ],
        )
        self.assertEqual(len(dto.attachments), 1)
        attachment = dto.attachments[0]
        self.assertIsInstance(attachment, Attachment)
        self.assertEqual(attachment.path, "/tmp/file.xml")
        self.assertEqual(attachment.file_type, "fgdc_xml")

    def test_with_audit_event_appends_entry(self) -> None:
        dto = build_canonical_dto(
            source_path="/tmp/FGDC-2.xml",
            zenodo_metadata={"title": "Audit Test"},
        )
        updated = dto.with_audit_event(
            "bibliographic_linkage",
            {"applied_at": "2025-10-15T00:00:00Z", "accepted_links": []},
        )
        self.assertEqual(dto.audit_trail, {})
        self.assertIn("bibliographic_linkage", updated.audit_trail)
        self.assertEqual(len(updated.audit_trail["bibliographic_linkage"]), 1)
        self.assertEqual(
            updated.audit_trail["bibliographic_linkage"][0]["applied_at"],
            "2025-10-15T00:00:00Z",
        )

    def test_copy_does_not_mutate_original(self) -> None:
        dto = build_canonical_dto(
            source_path="/tmp/FGDC-3.xml",
            zenodo_metadata={"title": "Clone Test"},
        )
        clone = dto.with_bibliographic_links(
            [
                BibliographicLink(
                    source="datacite",
                    identifier="https://doi.org/10.123/example",
                    relation="isAlternativeIdentifierOf",
                    confidence=0.9,
                )
            ]
        )
        self.assertEqual(len(dto.bibliographic_links), 0)
        self.assertEqual(len(clone.bibliographic_links), 1)


if __name__ == "__main__":
    unittest.main()

