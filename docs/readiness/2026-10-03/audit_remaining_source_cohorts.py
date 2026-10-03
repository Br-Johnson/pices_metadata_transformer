"""Verify exact reviewed raw metadata, originals, aliases and finite policy delta.

Only saved source/classification artifacts are read; no provider or credential access.
"""

import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Verify complete finite-source QA delta without provider access"
)
parser.add_argument("--before", type=Path, required=True)
parser.add_argument("--after", type=Path, required=True)
parser.add_argument("--frozen-baseline", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
R = Path(__file__).resolve().parents[3]
D = R / "docs/readiness/2026-10-03"
Q = {"before": args.before, "after": args.after}


def read(p):
    return json.loads(p.read_bytes())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fp(v):
    return hashlib.sha256(
        json.dumps(
            v, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


b = read(Q["before"] / "classification.json")
a = read(Q["after"] / "classification.json")
f = read(args.frozen_baseline / "classification.json") if args.frozen_baseline else b
br = {r["source_id"]: r for r in b["records"]}
ar = {r["source_id"]: r for r in a["records"]}
fr = {r["source_id"]: r for r in f["records"]}
assert b["summary"]["source_status_counts"] == {
    "supported": 3234,
    "held": 966,
    "failed": 6,
}
assert a["summary"]["source_status_counts"] == {
    "supported": 3468,
    "held": 732,
    "failed": 6,
}
cr = read(D / "source_citation_credits_409.json")
ti = read(D / "source_display_titles_35.json")
ac = read(D / "finite_source_resource_access_469.json")
creator = {m["source_id"] for c in cr["cohorts"][225:] for m in c["members"]}
titles = {m["source_id"] for m in ti["members"][8:]}
access = {m["source_id"] for m in ac["members"][264:]}
selected = creator | titles | access
promoted = access | titles | {"FGDC-2587", "FGDC-3788"}
assert len(selected) == 240 and len(promoted) == 234
assert cr["cohorts"][:225] == read(D / "source_citation_credits_401.json")["cohorts"]
assert ti["members"][:8] == read(D / "source_display_titles_8.json")["members"]
oldac = read(D / "finite_source_resource_access_264.json")
assert ac["members"][:264] == oldac["members"]
assert all(
    ac["acquisition_contexts"][k] == v for k, v in oldac["acquisition_contexts"].items()
)
receipt = read(D / "remaining_source_cohorts_complete_delta.json")
if args.frozen_baseline:
    assert (
        sha(args.frozen_baseline / "classification.json")
        == receipt["frozen_baseline_report_sha256"]
    )
creator_bindings = receipt["complete_creator_metadata_bindings"]
title_bindings = {m["source_id"]: m for m in ti["members"][8:]}
originals = []
copies = []
metas = []
policy_changes = {}
changed = []
actual_promoted = []
retained_creators = {}
payload_unchanged = 0
for sid in sorted(br):
    source = R / "FGDC" / (sid + ".xml")
    digest = sha(source)
    assert (
        br[sid]["source_sha256"]
        == ar[sid]["source_sha256"]
        == fr[sid]["source_sha256"]
        == digest
    )
    originals.append([sid, digest])
    for k in (
        "source_status",
        "hold_reasons",
        "exact_copy_aliases",
        "source_status_without_aliases",
    ):
        assert br[sid].get(k) == fr[sid].get(k), (sid, k, "frozen baseline drift")
    for k in (
        "exact_copy_aliases",
        "raw_primary_date",
        "raw_metadata_date",
        "raw_metadata_rights",
        "raw_metadata_access",
        "metadata_date_precision",
        "primary_date_stratum",
        "has_supported_xml_grant",
        "rehosting_authority",
        "new_reuse_license",
        "remote_verified",
        "publication_approved",
    ):
        assert br[sid].get(k) == ar[sid].get(k), (sid, k)
    assert (
        ar[sid]["remote_verified"] is False and ar[sid]["publication_approved"] is False
    )
    if sid in promoted:
        assert (
            br[sid]["source_status"] == "held"
            and ar[sid]["source_status"] == "supported"
        )
        actual_promoted.append(sid)
    elif sid in creator:
        assert ar[sid]["source_status"] == "held"
        retained_creators[sid] = ar[sid]["hold_reasons"]
        assert all("creator" not in r.lower() for r in ar[sid]["hold_reasons"])
    else:
        assert br[sid]["source_status"] == ar[sid]["source_status"]
        assert br[sid]["hold_reasons"] == ar[sid]["hold_reasons"]
    copy = Q["after"] / "data/original_fgdc" / (sid + ".xml")
    if copy.exists():
        assert sha(copy) == digest
        copies.append([sid, digest])
    path = Q["after"] / "data/zenodo_json" / (sid + ".json")
    if not path.exists():
        continue
    before = read(Q["before"] / "data/zenodo_json" / (sid + ".json"))
    after = read(path)
    frozen = (
        read(args.frozen_baseline / "data/zenodo_json" / (sid + ".json"))
        if args.frozen_baseline
        else before
    )
    assert before["metadata"] == frozen["metadata"]
    if sid in creator:
        binding = creator_bindings[sid]
        assert fp(before["metadata"]) == binding["before_sha256"]
        assert fp(after["metadata"]) == binding["actual_after_sha256"]
        changed.append(sid)
    elif sid in titles:
        binding = title_bindings[sid]
        assert fp(before["metadata"]) == binding["metadata_before_sha256"]
        assert fp(after["metadata"]) == binding["metadata_after_sha256"]
        changed.append(sid)
    else:
        assert before["metadata"] == after["metadata"], (
            sid,
            "unreviewed metadata change",
        )
    assert before["content_classification"] == after["content_classification"]
    assert (
        after["metadata"]["license"] == ""
        and after["metadata"]["access_right"] == "restricted"
    )
    metas.append([sid, fp(before["metadata"]), fp(after["metadata"])])
    oldpolicy = before["artifact_policy"]
    newpolicy = after["artifact_policy"]
    changes = {
        k
        for k in set(oldpolicy) | set(newpolicy)
        if oldpolicy.get(k) != newpolicy.get(k)
    }
    assert changes <= {
        "creator_interpretation",
        "source_title_interpretation",
        "dataset_access_interpretation",
    }, (sid, changes)
    for key in changes:
        target = (
            cr
            if key == "creator_interpretation"
            else ti
            if key == "source_title_interpretation"
            else ac
        )
        members = (
            [m for c in target["cohorts"] for m in c["members"]]
            if key == "creator_interpretation"
            else target["members"]
        )
        assert any(
            m["source_id"] == sid and m["source_sha256"] == digest for m in members
        )
        profile = D / (
            "source_citation_credits_409.json"
            if key == "creator_interpretation"
            else "source_display_titles_35.json"
            if key == "source_title_interpretation"
            else "finite_source_resource_access_469.json"
        )
        assert newpolicy[key]["manifest_sha256"] == sha(profile)
        policy_changes.setdefault(key, []).append(sid)
    if not changes:
        assert (
            Q["before"] / "data/zenodo_json" / (sid + ".json")
        ).read_bytes() == path.read_bytes()
        payload_unchanged += 1
assert (
    len(originals) == 4206
    and len(copies) == 4200
    and len(metas) == 4194
    and len(changed) == 35
)
aliases = [sid for sid, r in ar.items() if r["exact_copy_aliases"]]
assert len(aliases) == 456
assert all(ar[sid]["source_status"] == "held" for sid in aliases)
assert sorted(actual_promoted) == sorted(promoted)
for sid in ("FGDC-1238", "FGDC-2043", "FGDC-2057", "FGDC-2725", "FGDC-2731"):
    assert sid not in selected and ar[sid]["source_status"] == "supported"
residuals = [
    r
    for r in ar.values()
    if r["source_status"] == "held" and not r["exact_copy_aliases"]
]
assert len(residuals) == 276
counts = {}
for row in residuals:
    for reason in row["hold_reasons"]:
        counts[reason] = counts.get(reason, 0) + 1
result = {
    "schema_version": 1,
    "scope": "Complete offline corpus comparison against frozen821 and same-time old-profile baseline",
    "runtime_commit": "d611e1ca02d06306b26649661e60ae4b64a37927",
    "reviewed_at": a["reviewed_at"],
    "frozen_baseline_report_sha256": sha(args.frozen_baseline / "classification.json")
    if args.frozen_baseline
    else None,
    "same_time_baseline_report_sha256": sha(Q["before"] / "classification.json"),
    "after_report_sha256": sha(Q["after"] / "classification.json"),
    "summary": a["summary"],
    "originals_verified": 4206,
    "copies_verified": 4200,
    "constructed_full_raw_metadata_objects_verified": 4194,
    "raw_metadata_objects_unchanged": 4159,
    "reviewed_creator_metadata_changes": 8,
    "reviewed_title_metadata_changes": 27,
    "changed_source_ids": changed,
    "title_complete_before_after_objects_match_proposal_packet": True,
    "creator_complete_objects_match_proposal_with_existing_classifier_preservation_notes_before_final_generic_line": True,
    "original_inventory_sha256": fp(originals),
    "copy_inventory_sha256": fp(copies),
    "metadata_delta_inventory_sha256": fp(metas),
    "promotions": 234,
    "promotions_by_lane": {"access": 205, "title": 27, "creator": 2},
    "promoted_source_ids": actual_promoted,
    "creator_repairs_retaining_access_holds": retained_creators,
    "policy_rebindings_counts": {k: len(v) for k, v in policy_changes.items()},
    "policy_rebindings_inventory_sha256": fp(policy_changes),
    "same_time_payload_bytes_unchanged_without_policy_rebinding": payload_unchanged,
    "old_profile_members_contexts_verbatim": True,
    "all_outside_selected_statuses_hold_reasons_unchanged": True,
    "aliases_held": 456,
    "residual_nonalias_holds": 276,
    "source_date_repairs": 0,
    "new_licenses": 0,
    "remote_verified": 0,
    "publication_approved": 0,
    "provider_requests": 0,
    "provider_writes": 0,
    "five_existing_import_raw_metadata_unchanged": True,
    "residual_nonalias_reason_counts": counts,
}
p = args.output
p.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(
    json.dumps(
        {
            k: v
            for k, v in result.items()
            if k
            not in (
                "promoted_source_ids",
                "changed_source_ids",
                "residual_nonalias_reason_counts",
                "creator_repairs_retaining_access_holds",
            )
        },
        indent=2,
    )
)
print("audit_sha256", sha(p))
