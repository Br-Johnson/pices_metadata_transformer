#!/usr/bin/env python3
"""Map the frozen 456 aliases to byte content; select no catalogue identities.

Reads pinned, committed evidence and all original FGDC files. Recomputes hashes
and compares each repeated hash's raw bytes. Writes analysis artifacts only;
does not import the transformer, classify metadata, or contact a provider.
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE_COMMIT = "e998e9c97945da60cf9c15fb39ab5fc2a5b11d47"
BASE_TREE = "c8fc2d2b0e054c72df9f980f156ef9725db7df0e"
LEDGER = "docs/readiness/2026-10-04/residual_source32_integrated_source_status.json"
ALIASES = "docs/readiness/2026-10-03/source_alias_candidates.json"
SOURCE_EVIDENCE = "docs/readiness/2026-10-04/residual_alias_source_evidence.json"
PINS = {
    LEDGER: "8d70adb44b599f7b0707f3565d43b2356ee7973054ca66c5592f3826a2c555f2",
    ALIASES: "d1b5aae5446e230d86fd4a91b6385548b8d6c4fa93a3b98a0ccc26fc731f22d5",
    SOURCE_EVIDENCE: "82b923a4c8bccdc791924e298189eb23b8879076f25dff41e7a3a755770e3a61",
}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def object_digest(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_order(source_id):
    return int(source_id.removeprefix("FGDC-"))


def read_pinned(repo, relative):
    raw = (repo / relative).read_bytes()
    require(digest(raw) == PINS[relative], f"Pinned evidence changed: {relative}")
    return json.loads(raw)


def build(repo):
    ledger = read_pinned(repo, LEDGER)
    old = read_pinned(repo, ALIASES)
    evidence = read_pinned(repo, SOURCE_EVIDENCE)
    require(evidence["scope"]["canonical_selections"] == 0,
            "Source evidence no longer records zero canonical selections")
    status = {row["source_id"]: row for row in ledger["records"]}
    require(len(status) == len(ledger["records"]) == 4206,
            "Expected 4206 distinct ledger source identities")
    paths = sorted((repo / "FGDC").glob("*.xml"), key=lambda p: source_order(p.stem))
    require({p.stem for p in paths} == set(status), "XML and ledger identity sets differ")

    by_hash = defaultdict(list)
    first_bytes = {}
    inventory = []
    equality_comparisons = 0
    for path in paths:
        raw = path.read_bytes()
        sha = digest(raw)
        sid = path.stem
        require(sha == status[sid]["source_sha256"], f"Source bytes changed: {sid}")
        if sha in first_bytes:
            require(raw == first_bytes[sha], f"Equal hashes but unequal bytes: {sid}")
            equality_comparisons += 1
        else:
            first_bytes[sha] = raw
        by_hash[sha].append(sid)
        inventory.append({"source_id": sid, "source_sha256": sha,
                          "baseline_source_status": status[sid]["source_status"]})

    duplicate_groups = {sha: ids for sha, ids in by_hash.items() if len(ids) > 1}
    prior_groups = {row["source_sha256"]: row for row in old["groups"]}
    require(duplicate_groups == {sha: row["member_source_ids"]
                                for sha, row in prior_groups.items()},
            "All-corpus duplicate membership differs from the frozen alias groups")
    require(len(duplicate_groups) == 228 and
            all(len(ids) == 2 for ids in duplicate_groups.values()),
            "Expected 228 two-member groups")
    alias_ids = {sid for ids in duplicate_groups.values() for sid in ids}
    require(alias_ids == set(old["source_alias_to_candidate_canonical"]),
            "Frozen per-source alias coverage differs")
    require(len(alias_ids) == 456, "Expected all 456 alias identities")
    require(all(status[sid]["source_status"] == "held" for sid in alias_ids),
            "Baseline alias status changed")
    raw_counts = dict(Counter(row["source_status"] for row in status.values()))
    require(raw_counts == {"supported": 3677, "held": 523, "failed": 6},
            "Baseline ledger totals changed")
    require(ledger["integrated_counts"] == {"supported": 3677, "held": 523,
                                          "malformed": 6},
            "Baseline summary totals changed")

    rows = []
    historical_counts = Counter()
    historical_group_counts = Counter()
    groups = []
    for sha, ids in sorted(duplicate_groups.items()):
        prior = prior_groups[sha]
        historical = [old["source_alias_to_candidate_canonical"][sid] for sid in ids]
        require(all(row["source_sha256"] == sha for row in historical),
                "Historical source hash differs")
        diagnoses = {row["source_status_without_aliases"] for row in historical}
        require(len(diagnoses) == 1, "Historical component statuses disagree within a pair")
        historical_group_counts[next(iter(diagnoses))] += 1
        groups.append({
            "canonical_content_id": f"sha256:{sha}",
            "content_canonical_sha256": sha,
            "equivalence_group_members": ids,
            "member_count": len(ids),
            "extra_copies": len(ids) - 1,
            "all_member_raw_bytes_equal_verified": True,
            "baseline_member_source_statuses": {sid: status[sid]["source_status"] for sid in ids},
            "baseline_supported_members": [],
            "canonical_source_id": None,
            "canonical_catalogue_record_id": None,
            "canonical_provider_record_id": None,
            "canonical_provider_doi": None,
            "historical_title_from_frozen_alias_review": prior["title"],
            "historical_literal_procite_references": prior["literal_procite_references"],
            "historical_title_collision_warnings": prior["title_only_protected_record_warnings"],
        })
        for sid, previous in zip(ids, historical, strict=True):
            historical_counts[previous["source_status_without_aliases"]] += 1
            rows.append({
                "source_id": sid,
                "source_path": f"FGDC/{sid}.xml",
                "source_sha256": sha,
                "baseline_source_status": status[sid]["source_status"],
                "baseline_ledger_record": status[sid],
                "canonical_content_id": f"sha256:{sha}",
                "content_canonical_sha256": sha,
                "equivalence_group_members": ids,
                "raw_byte_equality_verified": True,
                "canonical_source_id": None,
                "canonical_catalogue_record_id": None,
                "canonical_provider_record_id": None,
                "canonical_provider_doi": None,
                "canonical_identity_evidence_status": "not_established",
                "historical_component_diagnostics_not_current_qa": {
                    "source_status_without_aliases": previous["source_status_without_aliases"],
                    "hold_reasons": previous["hold_reasons"],
                },
            })
    rows.sort(key=lambda row: source_order(row["source_id"]))
    require(historical_counts == {"supported": 408, "held": 48},
            "Frozen historical component totals changed")
    require(historical_group_counts == {"supported": 204, "held": 24},
            "Frozen historical pair component totals changed")

    return {
        "schema_version": 1,
        "analysis_only": True,
        "scope": "Complete per-source mapping of all 456 exact-byte aliases in the 4206-file corpus; no other per-source rows.",
        "baseline": {"commit": BASE_COMMIT, "tree": BASE_TREE,
                     "ledger_path": LEDGER, "ledger_sha256": PINS[LEDGER],
                     "status_semantics": "Statuses are bound to this frozen baseline, not a later checkout HEAD or a new semantic assessment."},
        "input_sha256": PINS,
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "content_identity_semantics": "canonical_content_id is sha256:<SHA256 of original raw XML bytes>. It denotes a content class, never a selected filename, scientific dataset, catalogue record, provider record or DOI.",
        "canonical_source_identity_semantics": "All source/catalogue/provider canonical fields remain null because the supplied evidence establishes no authoritative preferred source or identity crosswalk. Member ordering is for display only.",
        "all_corpus_inventory_verification": {
            "source_files": len(paths), "all_original_sha256_match_baseline_ledger": True,
            "unique_raw_contents": len(by_hash), "duplicate_groups": len(groups),
            "files_in_duplicate_groups": len(rows), "raw_byte_equality_comparisons": equality_comparisons,
            "all_duplicate_groups_exactly_match_existing_alias_map": True,
            "extra_copies_beyond_one_per_content": len(paths) - len(by_hash),
            "baseline_raw_status_counts": raw_counts,
            "baseline_summary_counts": ledger["integrated_counts"],
            "status_label_note": "The six per-source failed rows are summarized as malformed by the pinned ledger.",
            "baseline_alias_status_counts": {"held": len(rows)},
            "baseline_non_alias_status_counts": dict(Counter(row["source_status"] for sid, row in status.items() if sid not in alias_ids)),
            "baseline_supported_exact_content_counterparts_to_aliases": 0,
            "complete_inventory_canonical_sha256": object_digest(inventory),
            "inventory_digest_recipe": "Source IDs in ascending numeric order; rows have source_id, source_sha256 and baseline_source_status; canonical JSON uses sorted keys, compact separators, ensure_ascii=False and UTF-8.",
        },
        "historical_component_diagnostics_not_current_qa": {
            "source_checkpoint": old["source_checkpoint"],
            "classification_sha256": old["classification_sha256"],
            "evidence_path": ALIASES, "evidence_sha256": PINS[ALIASES],
            "source_status_without_aliases": dict(historical_counts),
            "pair_status_without_aliases": dict(historical_group_counts),
            "meaning": "408 identities in 204 pairs were supported apart from the alias gate in this old assessment; 48 identities in 24 pairs had additional holds. Both members of every pair remain baseline held. No current component QA, promotion or release is inferred.",
        },
        "groups": groups,
        "source_to_content": rows,
        "groups_canonical_sha256": object_digest(groups),
        "source_to_content_canonical_sha256": object_digest(rows),
        "effects": {"source_edits": 0, "canonical_source_selections": 0,
                    "source_promotions": 0, "provider_requests": 0,
                    "record_collapse_or_deletion": 0, "publication_approvals": 0},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    require(not args.output_dir.resolve().is_relative_to(args.repo.resolve()),
            "Analysis output must be outside the source checkout")
    manifest = build(args.repo)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "alias456_source_to_content.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["source_id", "source_path", "source_sha256", "baseline_source_status",
              "canonical_content_id", "canonical_source_id", "canonical_catalogue_record_id",
              "canonical_provider_record_id", "canonical_provider_doi",
              "equivalence_group_members", "raw_byte_equality_verified"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in manifest["source_to_content"]:
        out = {key: row[key] for key in fields}
        out["equivalence_group_members"] = ";".join(out["equivalence_group_members"])
        writer.writerow(out)
    csv_path = args.output_dir / "alias456_source_to_content.csv"
    csv_path.write_text(stream.getvalue(), encoding="utf-8", newline="")
    print(json.dumps({"manifest": str(manifest_path), "manifest_sha256": digest(manifest_path.read_bytes()),
                      "csv": str(csv_path), "csv_sha256": digest(csv_path.read_bytes()),
                      "rows": len(manifest["source_to_content"]), "groups": len(manifest["groups"])}))


if __name__ == "__main__":
    main()
