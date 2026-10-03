"""Reproduce finite-source QA with fixture tokens and network/DNS prohibited."""

import argparse
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def forbidden(*args, **kwargs):
    raise AssertionError("Provider transport and DNS forbidden in offline source QA")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("test")
    classify = sub.add_parser("classify")
    classify.add_argument("--source-dir", type=Path, default=REPO / "FGDC")
    classify.add_argument("--output", type=Path, required=True)
    classify.add_argument("--reviewed-at", required=True)
    classify.add_argument("--old-profiles", action="store_true")
    args = parser.parse_args()
    os.chdir(REPO)
    os.environ["ZENODO_SANDBOX_TOKEN"] = "offline-fixture-token"
    os.environ["ZENODO_PRODUCTION_TOKEN"] = "offline-fixture-token"
    with (
        patch("requests.sessions.Session.send", forbidden),
        patch("socket.socket.connect", forbidden),
        patch("socket.create_connection", forbidden),
        patch("socket.getaddrinfo", forbidden),
    ):
        if args.mode == "test":
            result = unittest.TextTestRunner(verbosity=1).run(
                unittest.defaultTestLoader.discover(str(REPO / "tests"))
            )
            return 0 if result.wasSuccessful() else 1
        from scripts.collection_qa import classify_collection

        docs = Path("docs/readiness/2026-10-03")
        old = Path("docs/readiness/2026-10-02")
        report = classify_collection(
            args.source_dir,
            args.output,
            args.reviewed_at,
            authority_manifest=old / "rehosting_authority.json",
            access_interpretation_manifest=old / "contact_source_interpretation.json",
            creator_interpretation_manifest=old / "exxon_citation_interpretation.json",
            dataset_access_interpretation_manifest=docs
            / (
                "finite_source_resource_access_264.json"
                if args.old_profiles
                else "finite_source_resource_access_469.json"
            ),
            contributor_access_interpretation_manifest=old
            / "contributor_source_interpretation.json",
            collective_creator_interpretation_manifest=docs
            / "dfo_staff_citation_interpretation.json",
            institution_creator_interpretation_manifest=docs
            / (
                "source_citation_credits_401.json"
                if args.old_profiles
                else "source_citation_credits_409.json"
            ),
            source_link_interpretation_manifest=docs
            / "historical_dataset_linkage_21.json",
            source_title_interpretation_manifest=docs
            / (
                "source_display_titles_8.json"
                if args.old_profiles
                else "source_display_titles_35.json"
            ),
            source_scope_attestation_manifest=docs
            / "source_scope_attestation_821.json",
        )
        print(report["summary"])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
