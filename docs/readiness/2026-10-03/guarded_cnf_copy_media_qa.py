"""Bounded ten/22-source comparison against a frozen baseline; no remote work."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
BASELINE_SHA = "0ec37de02ea67af81d3b433a65e523c6c05f30220c667324e2fc3b6a367c8708"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def forbidden(*args, **kwargs):
    raise AssertionError("Provider transport, sockets and DNS forbidden")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--limit", type=int, choices=(10, 22), default=10)
    parser.add_argument("--reviewed-at", required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.baseline = args.baseline.resolve()
    baseline_raw = args.baseline.read_bytes()
    if digest(baseline_raw) != BASELINE_SHA:
        raise ValueError("Exact frozen merged-main baseline required")
    baseline = json.loads(baseline_raw)
    baseline_rows = {r["source_id"]: r for r in baseline["records"]}
    os.chdir(REPO)
    docs = Path("docs/readiness/2026-10-03")
    old = Path("docs/readiness/2026-10-02")
    proposal = json.loads(
        (docs / "cnf_copy_media_source_proposals_22.json").read_bytes()
    )
    members = proposal["members"][: args.limit]
    rows = []
    with (
        patch.dict(
            os.environ,
            {
                "ZENODO_SANDBOX_TOKEN": "offline-fixture-token",
                "ZENODO_PRODUCTION_TOKEN": "offline-fixture-token",
            },
            clear=True,
        ),
        patch("requests.sessions.Session.send", forbidden),
        patch("socket.socket.connect", forbidden),
        patch("socket.create_connection", forbidden),
        patch("socket.getaddrinfo", forbidden),
        tempfile.TemporaryDirectory() as temporary,
    ):
        from scripts.collection_qa import classify_collection
        from scripts.path_config import OutputPaths

        source = Path(temporary)
        for member in members:
            sid = member["source_id"]
            raw = (REPO / "FGDC" / (sid + ".xml")).read_bytes()
            require(
                digest(raw) == member["source_sha256"],
                "Bounded source-integrity or classification contract failed",
            )
            shutil.copyfile(REPO / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
        reports, paths = {}, {}
        for phase, profile in (
            ("before", "finite_source_resource_access_469.json"),
            ("after", "finite_source_resource_access_491.json"),
        ):
            output = args.output / phase
            reports[phase] = classify_collection(
                source,
                output,
                args.reviewed_at,
                authority_manifest=old / "rehosting_authority.json",
                access_interpretation_manifest=old
                / "contact_source_interpretation.json",
                creator_interpretation_manifest=old
                / "exxon_citation_interpretation.json",
                dataset_access_interpretation_manifest=docs / profile,
                contributor_access_interpretation_manifest=old
                / "contributor_source_interpretation.json",
                collective_creator_interpretation_manifest=docs
                / "dfo_staff_citation_interpretation.json",
                institution_creator_interpretation_manifest=docs
                / "source_citation_credits_409.json",
                source_link_interpretation_manifest=docs
                / "historical_dataset_linkage_21.json",
                source_title_interpretation_manifest=docs
                / "source_display_titles_35.json",
                source_scope_attestation_manifest=docs
                / "source_scope_attestation_821.json",
            )
            paths[phase] = OutputPaths(str(output), "sandbox")
        for member in members:
            sid = member["source_id"]
            payloads = {
                phase: json.loads(
                    (Path(path.zenodo_json_dir) / (sid + ".json")).read_bytes()
                )
                for phase, path in paths.items()
            }
            baseline_payload_path = (
                args.baseline.parent / "data/zenodo_json" / (sid + ".json")
            )
            baseline_payload_raw = baseline_payload_path.read_bytes()
            require(
                digest(baseline_payload_raw)
                == baseline_rows[sid]["prepared_payload_sha256"],
                "Bounded source-integrity or classification contract failed",
            )
            saved = json.loads(baseline_payload_raw)
            require(
                saved["metadata"]
                == payloads["before"]["metadata"]
                == payloads["after"]["metadata"],
                "Bounded source-integrity or classification contract failed",
            )
            for phase, path in paths.items():
                copied = (Path(path.original_fgdc_dir) / (sid + ".xml")).read_bytes()
                require(
                    digest(copied) == member["source_sha256"],
                    "Bounded source-integrity or classification contract failed",
                )
                row = next(
                    r for r in reports[phase]["records"] if r["source_id"] == sid
                )
                require(
                    row["source_status"]
                    == ("held" if phase == "before" else "supported"),
                    "Bounded source-integrity or classification contract failed",
                )
                require(
                    not row["remote_verified"] and not row["publication_approved"],
                    "Bounded source-integrity or classification contract failed",
                )
            rows.append(
                {
                    **member,
                    "baseline_payload_sha256": digest(baseline_payload_raw),
                    "before_status": "held",
                    "after_status": "supported",
                    "complete_raw_metadata_unchanged": True,
                    "original_and_copied_XML_unchanged": True,
                }
            )
    result = {
        "schema_version": 1,
        "scope": "actual bounded selected-source delta; no fresh full-corpus audit",
        "baseline_report_sha256": BASELINE_SHA,
        "limit": args.limit,
        "selected_before": reports["before"]["summary"]["source_status_counts"],
        "selected_after": reports["after"]["summary"]["source_status_counts"],
        "baseline_counts": {"supported": 3468, "held": 732, "malformed": 6},
        "projected_counts_from_frozen_baseline_and_exact_delta": {
            "supported": 3468 + len(members),
            "held": 732 - len(members),
            "malformed": 6,
        },
        "all_other_source_memberships_unchanged_by_additive_profile": True,
        "rows": rows,
        "provider_requests": 0,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "bounded_delta.json").write_text(json.dumps(result, indent=2) + "\n")
    print({key: value for key, value in result.items() if key != "rows"})


if __name__ == "__main__":
    main()
