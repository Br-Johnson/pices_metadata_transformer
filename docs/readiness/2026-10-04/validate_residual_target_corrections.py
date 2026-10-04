"""Finite reviewed source corrections and class semantic deltas, strictly offline."""

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

BASE = "9bac0ace68c83a2082168f022315c05a1192210b"
DOCS = "docs/readiness/2026-10-04/"
LEDGER = DOCS + "creator8_integrated_source_status.json"
TARGETS = DOCS + "creator8_record_target_projection.json"
OLD = {
    "creator": DOCS + "source_citation_credits_423.json",
    "access": DOCS + "finite_source_resource_access_607.json",
    "title": DOCS + "source_display_titles_36.json",
}
# Root freezes these exact candidate filenames and their independently reviewed scope before execution.
NEW = {
    "creator": DOCS + "source_citation_credits_426.json",
    "access": DOCS + "finite_source_resource_access_655.json",
    "title": DOCS + "source_display_titles_42.json",
}
PINS = {
    LEDGER: "3b3f255c6c4f6f921acd07bd20e57fb2f753099332475962438efc7f4b19bb4a",
    TARGETS: "2da9926b1cf7344165c83a3338ec523ac7f2461744c503dfada43cd7d311abbc",
    OLD["creator"]: "c720de8c0775adf3b432fc4bc5e28bdfbb36c67ceb91b73b719d0179cf8f8bf6",
    OLD["access"]: "83bdb0b1ab689e5fbf844467975ad9d279b6bba759cb3db3a18a11704715679c",
    OLD["title"]: "c776b324f43a3e7560ef016f12b7a345bbb2f21cc016b74bd5298b8ed1e10781",
    "ci/run_offline_tests.py": "1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05",
}
EXPECTED_CLASS_TRANSITIONS = {
    "sha256:26fdd51ab6cf1a96245eb1609d7732dd34fe8a74ffe9b0ff3b780c8d750ca8a8": {
        "before": "held",
        "after": "supported",
    },
    "sha256:29238d857a6e7542b14e1efc34964d57be39852a90de70712fd9028c9c8a1eab": {
        "before": "held",
        "after": "supported",
    },
    "sha256:327e3be013aa03c2795f19a8e79cafc59dfce5628efe0c0eff970ea68461afdd": {
        "before": "held",
        "after": "supported",
    },
    "sha256:41d91946ae8c93520bb49b6cfc1b60aad634489ac2e45de9ff4fa4c891684bec": {
        "before": "held",
        "after": "supported",
    },
    "sha256:4385a97b249dfbe21ef694ae80bc40c0f7b409f0cdc4b4705f532a90f1549914": {
        "before": "held",
        "after": "supported",
    },
    "sha256:43f274d62e355529dce0cda7a351796d106f0b9571f68d7ae51a33dd9705c002": {
        "before": "held",
        "after": "supported",
    },
    "sha256:51e1a0c3dbac56958c4d0452dc87558162302a6273e33d237cc74ff4ec79aaf9": {
        "before": "held",
        "after": "supported",
    },
    "sha256:650a2e277e5800d95a1ff7017ef08e029a438d9d79396eed0e63af5d213d412c": {
        "before": "held",
        "after": "supported",
    },
    "sha256:6e73f6729dcfd517429864b8e189f6ac9597b638c8a011c5a5bbc494c7b84f7f": {
        "before": "held",
        "after": "supported",
    },
    "sha256:80c261cd5465afee8dab90e7428160c66b0ca63a5482a9733784e51c91c2778a": {
        "before": "held",
        "after": "supported",
    },
    "sha256:8bef14fd05c7b1ea1ab936bfeb4c5325c29c34f33b46d40b6f82f72055973237": {
        "before": "held",
        "after": "supported",
    },
    "sha256:921e4abfddf9d47993f0c606b970035b88ffe2562bad03b6691ce46cbc7eb89b": {
        "before": "held",
        "after": "supported",
    },
    "sha256:927bb889e309c91bdbd22053c78bfb88e9f37d6f693ef785c3679dc892dd024f": {
        "before": "held",
        "after": "supported",
    },
    "sha256:a65bcdaf08b02f83bb2813a14edb2733a207fcc007a4c41cfd34aef348df024a": {
        "before": "held",
        "after": "supported",
    },
    "sha256:b894b4d7dacde8dff0994f6c761d2bc25d1ec580927f74fa84cd5f5676defc44": {
        "before": "held",
        "after": "supported",
    },
    "sha256:ca9a74702d046a13e70abac603f87b17618ecd2a70c51f1363c80629f574f615": {
        "before": "held",
        "after": "supported",
    },
    "sha256:d3c01de168200db59092a5d24e0d0b302042b772488fada1b8d381e700e83df3": {
        "before": "held",
        "after": "supported",
    },
    "sha256:d62c478268c54ac21ba33336fec9c930554165bdf0882217f0863aea4d4d68ae": {
        "before": "held",
        "after": "supported",
    },
    "sha256:d67382ea4475d9d44e1214a171cb98a1a06edd6ce32559694133904e59ae6fb0": {
        "before": "held",
        "after": "supported",
    },
    "sha256:e6160e2ad93b28764b4fc16f021b58b8fbc9f8e02fa9d0f7a2abcb3905c203ac": {
        "before": "held",
        "after": "supported",
    },
    "sha256:ebcdb3f1f6d5210c3ccb49c59acbb0af3e1bc8f022ef9e56c84317d952e0f76b": {
        "before": "held",
        "after": "supported",
    },
    "sha256:f02fcbd12d5147acc0951e4d8ed5e475891937443240c06b8c7062d61fcf9368": {
        "before": "held",
        "after": "supported",
    },
    "sha256:f3cb8a667d674df59c9552569750453e3e9584d80499e3b5fea1bbc7fc9fff78": {
        "before": "held",
        "after": "supported",
    },
    "sha256:fcf77e5bcd5b5e65b25dcfaa7e0db91f2aac3cd875649f3428eb3a93b6644833": {
        "before": "held",
        "after": "supported",
    },
}
CONTROL_PAIR = {"FGDC-2953", "FGDC-3181"}
HELD_CONTROL = "FGDC-288"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()


def require(test, message):
    if not test:
        raise AssertionError(message)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def reference(path):
    return {"manifest_path": str(path), "manifest_sha256": sha(path.read_bytes())}


def file_ref(path, output):
    raw = path.read_bytes()
    return {
        "path": str(path.relative_to(output)),
        "sha256": sha(raw),
        "bytes": len(raw),
    }


def inventory(repo):
    return {p.stem: sha(p.read_bytes()) for p in sorted((repo / "FGDC").glob("*.xml"))}


def classify_options(repo, active):
    older, previous = (
        repo / "docs/readiness/2026-10-02",
        repo / "docs/readiness/2026-10-03",
    )
    chosen = NEW if active else OLD
    return {
        "authority_manifest": older / "rehosting_authority.json",
        "access_interpretation_manifest": older / "contact_source_interpretation.json",
        "creator_interpretation_manifest": older / "exxon_citation_interpretation.json",
        "contributor_access_interpretation_manifest": older
        / "contributor_source_interpretation.json",
        "collective_creator_interpretation_manifest": previous
        / "dfo_staff_citation_interpretation.json",
        "source_link_interpretation_manifest": previous
        / "historical_dataset_linkage_21.json",
        "source_scope_attestation_manifest": previous
        / "source_scope_reconciliation_904.json",
        "institution_creator_interpretation_manifest": repo / chosen["creator"],
        "dataset_access_interpretation_manifest": repo / chosen["access"],
        "source_title_interpretation_manifest": repo / chosen["title"],
    }


def additions(repo):
    profiles, ids = {}, {}
    for axis in OLD:
        old, new = (
            json.loads((repo / names[axis]).read_bytes()) for names in (OLD, NEW)
        )
        key = "cohorts" if axis == "creator" else "members"
        require(
            new[key][: len(old[key])] == old[key],
            "Earlier profile objects changed: " + axis,
        )
        require(
            new["prior_manifest_sha256"] == PINS[OLD[axis]], "Profile lineage changed"
        )
        if axis == "creator":
            members = [
                m for cohort in new[key][len(old[key]) :] for m in cohort["members"]
            ]
        else:
            members = new[key][len(old[key]) :]
        ids[axis] = {m["source_id"] for m in members}
        require(
            len(ids[axis]) == len(members) and members,
            "Finite additions missing or duplicated",
        )
        if axis == "access":
            require(
                all(
                    new["source_contexts"][sid] == context
                    for sid, context in old["source_contexts"].items()
                ),
                "Earlier registration source contexts changed",
            )
            require(
                all(
                    new["acquisition_contexts"][sid] == context
                    for sid, context in old["acquisition_contexts"].items()
                ),
                "Earlier resource contexts changed",
            )
            require(
                all(new[k] == v for k, v in old.items() if k.endswith("_review")),
                "Historical access review blocks changed",
            )
        profiles[axis] = new
    require(
        not ids["creator"] & ids["title"],
        "Creator/title overlap requires a separately bound composed metadata image",
    )
    return profiles, ids


def creator_notes(before, after, result):
    restored = after
    for note in result["preservation_notes"]:
        require("\n" + note in restored, "Missing creator context")
        restored = restored.replace("\n" + note, "", 1)
    old = [
        line for line in before.splitlines() if line.startswith("Curator decision: ")
    ]
    new = [
        line for line in restored.splitlines() if line.startswith("Curator decision: ")
    ]
    require(len(old) == len(new) == 1, "Expected one creator decision")
    a, b = (
        json.loads(lines[0].removeprefix("Curator decision: ")) for lines in (old, new)
    )
    b["metadata"]["creators"] = a["metadata"]["creators"]
    require(
        a == b and restored.replace(new[0], old[0], 1) == before,
        "Unreviewed creator note delta",
    )


def validate(repo, output, reviewed_at, revision, guard):
    import scripts.logger
    from ci.run_offline_tests import source_bindings

    scripts.logger.get_logger = lambda *args, **kwargs: Mock()
    from scripts.artifact_contract import prepare_artifact
    from scripts.citation_creator_interpretation import validate_creator_interpretation
    from scripts.collection_qa import classify_collection
    from scripts.content_class_targets import load_representation, prepare_class_target
    from scripts.dataset_access_interpretation import (
        validate_dataset_access_interpretation,
    )
    from scripts.path_config import OutputPaths
    from scripts.source_title_interpretation import validate_source_title_interpretation
    from scripts.upload_service import metadata_hash, prepare_metadata

    bindings = source_bindings(repo)
    for path, expected in PINS.items():
        require(
            sha((repo / path).read_bytes()) == expected, "Pinned input changed: " + path
        )
    ledger, historical = (
        json.loads((repo / path).read_bytes()) for path in (LEDGER, TARGETS)
    )
    source_rows = {r["source_id"]: r for r in ledger["records"]}
    originals = inventory(repo)
    require(
        len(originals) == 4206
        and originals == {sid: r["source_sha256"] for sid, r in source_rows.items()},
        "Original inventory changed",
    )
    profiles, ids = additions(repo)
    candidates = set.union(*ids.values())
    identities = load_representation()["classes"]
    aliases = {sid for row in identities for sid in row["source_ids"]}
    selected_classes = {
        row["record_target_id"]: row
        for row in identities
        if candidates.intersection(row["source_ids"])
    }
    require(
        all(set(row["source_ids"]) <= candidates for row in selected_classes.values()),
        "Every corrected class must include both members",
    )
    require(
        set(selected_classes) == set(EXPECTED_CLASS_TRANSITIONS),
        "Reviewed class scope differs",
    )
    singleton_ids = candidates - aliases
    require(singleton_ids == {"FGDC-2664"}, "Reviewed singleton scope differs")
    old_classes = {r["record_target_id"]: r for r in historical["class_targets"]}
    require(
        all(
            old_classes[cid]["source_semantic_status"] == "held"
            for cid in selected_classes
        ),
        "Candidate class was not held",
    )
    require(
        all(
            source_rows[sid]["source_status"] == "held"
            for sid in candidates | {HELD_CONTROL}
        ),
        "Candidate/control baseline changed",
    )
    require(
        not candidates & (CONTROL_PAIR | {HELD_CONTROL}), "Correction/control overlap"
    )
    reviewed = {}
    for axis, members in ids.items():
        for sid in sorted(members):
            root = ET.parse(repo / "FGDC" / (sid + ".xml")).getroot()
            ref = reference(repo / NEW[axis])
            if axis == "creator":
                result = validate_creator_interpretation(
                    ref, sid, originals[sid], root, True
                )
            elif axis == "access":
                result = validate_dataset_access_interpretation(
                    ref, sid, originals[sid], root, reviewed_at
                )
            else:
                result = validate_source_title_interpretation(
                    ref, sid, originals[sid], root
                )
            reviewed[(axis, sid)] = result
    # Four representative correction pairs plus one supported pair is a ten-source smoke.
    smoke = set(CONTROL_PAIR)
    for number in (2837, 2872, 2894, 2948):
        row = next(
            r
            for r in selected_classes.values()
            if "FGDC-" + str(number) in r["source_ids"]
        )
        smoke.update(row["source_ids"])
    require(len(smoke) == 10, "Smoke must use five complete pairs")
    batches, deltas, measured_classes = [], [], {}

    def measure(name, selected):
        directory = output / name
        source, prepared = directory / "sources", directory / "prepared"
        source.mkdir(parents=True)
        for sid in sorted(selected):
            shutil.copyfile(repo / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
        phase_data = {}
        print("START " + name + ": " + str(len(selected)) + " sources", flush=True)
        class_ids = [
            r["record_target_id"]
            for r in identities
            if set(r["source_ids"]) <= selected
        ]
        for phase in ("before", "after", "repeat", "withdrawn"):
            active = phase in ("after", "repeat")
            report = classify_collection(
                source, prepared, reviewed_at, **classify_options(repo, active)
            )
            paths = OutputPaths(str(prepared), "sandbox")
            rows = {row["source_id"]: row for row in report["records"]}
            require(
                set(rows) == selected and len(rows) == len(report["records"]),
                "Source coverage changed",
            )
            supported = singleton_ids & selected if active else set()
            require(
                report["summary"]["source_status_counts"]
                == {
                    "supported": len(supported),
                    "held": len(selected) - len(supported),
                    "failed": 0,
                },
                "Source counts or alias holds changed",
            )
            payloads, submitted, contracts = {}, {}, {}
            for sid in sorted(selected):
                p = Path(paths.zenodo_json_dir) / (sid + ".json")
                xml = Path(paths.original_fgdc_dir) / (sid + ".xml")
                raw = p.read_bytes()
                payload = json.loads(raw)
                payloads[sid] = payload
                require(
                    sha(xml.read_bytes()) == originals[sid]
                    and rows[sid]["source_sha256"] == originals[sid]
                    and rows[sid]["prepared_payload_sha256"] == sha(raw),
                    "Actual source/payload binding changed",
                )
                require(
                    rows[sid]["source_status"]
                    == ("supported" if sid in supported else "held"),
                    "Exact per-source state differs: " + phase + "/" + sid,
                )
                md, policy = payload["metadata"], payload["artifact_policy"]
                require(
                    md["access_right"] == "restricted"
                    and md["license"] == ""
                    and policy["rights_scope"] == "original_fgdc_xml"
                    and policy["rights_source_xpath"] == "./metainfo/metuc"
                    and policy["date_semantics"] == "source_metadata_date",
                    "Rights/date scope changed",
                )
                require(
                    rows[sid]["rehosting_authority"] == "USER_ATTESTED"
                    and not rows[sid]["remote_verified"]
                    and not rows[sid]["publication_approved"],
                    "Authority/release boundary changed",
                )
                if sid in aliases:
                    require(
                        rows[sid]["hold_reasons"].count(
                            "Exact-copy aliases require identity adjudication"
                        )
                        == 1,
                        "Source alias operation hold missing",
                    )
                submission, _, source_hash = prepare_metadata(str(p), paths)
                require(source_hash == originals[sid], "Submission source hash changed")
                submitted[sid] = submission
                contracts[sid] = prepare_artifact(payload, xml)
                if "metadata_sha256" in rows[sid]:
                    require(
                        rows[sid]["metadata_sha256"] == metadata_hash(submission),
                        "Submission hash differs",
                    )
            targets = {
                cid: prepare_class_target(cid, paths, reviewed_at=reviewed_at)
                for cid in class_ids
            }
            for cid, target in targets.items():
                wanted = (
                    EXPECTED_CLASS_TRANSITIONS[cid]["after" if active else "before"]
                    if cid in EXPECTED_CLASS_TRANSITIONS
                    else "supported"
                )
                require(
                    target["source_semantic_status"] == wanted,
                    "Class semantic delta differs",
                )
                require(
                    all(
                        x["source_semantic_status"] == wanted
                        for x in target["member_assessments"]
                    ),
                    "Both members must agree",
                )
                require(
                    not target["upload_eligible"]
                    and not target["remote_verified"]
                    and not target["publication_approved"]
                    and target["production_reconciliation_status"] == "pending"
                    and target["canonical_source_id"] is None
                    and target["canonical_provider_record_id"] is None,
                    "Class release or identity boundary changed",
                )
            snapshot = directory / (phase + "_snapshot")
            shutil.copytree(prepared, snapshot)
            write(snapshot / "measured_class_targets.json", targets)
            phase_data[phase] = {
                "report": report,
                "payloads": payloads,
                "submitted": submitted,
                "contracts": contracts,
                "targets": targets,
            }
        require(
            phase_data["after"] == phase_data["repeat"], "Same-output retry differs"
        )
        require(
            phase_data["before"] == phase_data["withdrawn"],
            "Withdrawal did not restore baseline",
        )
        before, after = phase_data["before"], phase_data["after"]
        keys = {
            "creator": "creator_interpretation",
            "access": "dataset_access_interpretation",
            "title": "source_title_interpretation",
        }
        for sid in sorted(selected):
            old, new = before["payloads"][sid], after["payloads"][sid]
            restored = copy.deepcopy(new)
            axis = next(
                (axis for axis in ("creator", "title", "access") if sid in ids[axis]),
                None,
            )
            if axis == "creator":
                require(
                    new["metadata"]["creators"] == reviewed[(axis, sid)]["creators"],
                    "Exact creator objects differ",
                )
                creator_notes(
                    old["metadata"]["notes"],
                    new["metadata"]["notes"],
                    reviewed[(axis, sid)],
                )
                require(
                    {
                        k: v
                        for k, v in old["metadata"].items()
                        if k not in ("creators", "notes")
                    }
                    == {
                        k: v
                        for k, v in new["metadata"].items()
                        if k not in ("creators", "notes")
                    },
                    "Unreviewed creator metadata delta",
                )
            elif axis == "title":
                member = reviewed[(axis, sid)]
                require(
                    sha(canonical(old["metadata"])) == member["metadata_before_sha256"]
                    and sha(canonical(new["metadata"]))
                    == member["metadata_after_sha256"],
                    "Complete title images differ",
                )
                expected = copy.deepcopy(old["metadata"])
                expected["title"] = member["display_title"]
                expected["notes"] += "\n\n" + member["preservation_note"]
                require(
                    new["metadata"] == expected,
                    "Title changed more than exact display and note",
                )
            else:
                require(
                    old["metadata"] == new["metadata"],
                    "Access/control raw metadata changed",
                )
            restored["metadata"] = copy.deepcopy(old["metadata"])
            for family, key in keys.items():
                old_ref, new_ref = (
                    reference(repo / OLD[family]),
                    reference(repo / NEW[family]),
                )
                if sid in ids[family]:
                    require(
                        key not in old["artifact_policy"]
                        and restored["artifact_policy"].pop(key) == new_ref,
                        "Correction policy reference differs",
                    )
                elif old["artifact_policy"].get(key) == old_ref:
                    require(
                        restored["artifact_policy"][key] == new_ref,
                        "Existing member profile upgrade differs",
                    )
                    restored["artifact_policy"][key] = old_ref
            require(
                restored == old,
                "Payload changed beyond exact reviewed metadata and references",
            )
            deltas.append(
                {
                    "batch": name,
                    "source_id": sid,
                    "axis": axis or "control",
                    "all_correction_axes": [
                        family for family in ids if sid in ids[family]
                    ],
                    "source_sha256": originals[sid],
                    "raw_metadata_before_sha256": sha(canonical(old["metadata"])),
                    "raw_metadata_after_sha256": sha(canonical(new["metadata"])),
                    "saved_phases": {
                        phase: {
                            "payload": file_ref(
                                directory
                                / (phase + "_snapshot/data/zenodo_json/")
                                / (sid + ".json"),
                                output,
                            ),
                            "original": file_ref(
                                directory
                                / (phase + "_snapshot/data/original_fgdc/")
                                / (sid + ".xml"),
                                output,
                            ),
                            "artifact_sha256": phase_data[phase]["contracts"][sid][
                                "sha256"
                            ],
                            "submission_sha256": sha(
                                canonical(phase_data[phase]["submitted"][sid])
                            ),
                        }
                        for phase in phase_data
                    },
                }
            )
        batches.append(
            {
                "name": name,
                "source_ids": sorted(selected),
                "complete_classes": class_ids,
                "same_output_repeat_exact": True,
                "same_output_withdrawal_exact": True,
                "classification_snapshots": {
                    phase: file_ref(
                        directory / (phase + "_snapshot/classification.json"), output
                    )
                    for phase in phase_data
                },
                "class_snapshots": {
                    phase: file_ref(
                        directory / (phase + "_snapshot/measured_class_targets.json"),
                        output,
                    )
                    for phase in phase_data
                },
            }
        )
        print("PASS " + name, flush=True)
        return phase_data

    smoke_result = measure("smoke10", smoke)
    full = measure("all_candidates", candidates | CONTROL_PAIR | {HELD_CONTROL})
    for phase in smoke_result:
        for sid in smoke:
            require(
                smoke_result[phase]["payloads"][sid] == full[phase]["payloads"][sid],
                "Smoke/full payload differs",
            )
        for cid, target in smoke_result[phase]["targets"].items():
            require(target == full[phase]["targets"][cid], "Smoke/full class differs")
    measured_classes = full["after"]["targets"]
    actual_transitions = {
        cid: {
            "before": full["before"]["targets"][cid]["source_semantic_status"],
            "after": measured_classes[cid]["source_semantic_status"],
        }
        for cid in selected_classes
    }
    require(
        actual_transitions == EXPECTED_CLASS_TRANSITIONS,
        "Actual transitions differ from finite reviewed outcomes",
    )
    actual_singleton_transitions = {
        sid: {
            phase: next(
                row["source_status"]
                for row in full[phase]["report"]["records"]
                if row["source_id"] == sid
            )
            for phase in ("before", "after")
        }
        for sid in singleton_ids
    }
    require(
        actual_singleton_transitions
        == {sid: {"before": "held", "after": "supported"} for sid in singleton_ids},
        "Exact measured singleton transitions differ",
    )
    promoted_singletons = {
        sid
        for sid, transition in actual_singleton_transitions.items()
        if transition == {"before": "held", "after": "supported"}
    }
    promoted_classes = {
        cid
        for cid, transition in actual_transitions.items()
        if transition == {"before": "held", "after": "supported"}
    }
    integrated = copy.deepcopy(ledger)
    for row in integrated["records"]:
        if row["source_id"] in promoted_singletons:
            row.update(
                source_status="supported",
                evidence="measured_residual_target_singleton_delta",
            )
        else:
            require(
                row == source_rows[row["source_id"]],
                "Unselected source ledger row changed",
            )
    source_counts = Counter(row["source_status"] for row in integrated["records"])
    require(
        source_counts
        == {
            "supported": 3704 + len(promoted_singletons),
            "held": 496 - len(promoted_singletons),
            "failed": 6,
        },
        "Source ledger counts differ",
    )
    if promoted_singletons:
        integrated.update(
            integrated_counts={
                "supported": source_counts["supported"],
                "held": source_counts["held"],
                "malformed": 6,
            },
            per_source_status_sha256=sha(canonical(integrated["records"])),
            scope="Frozen creator8 source ledger plus the exact measured singleton correction; class member file holds remain unchanged.",
            promoted_source_count=ledger["promoted_source_count"]
            + len(promoted_singletons),
            prior_source_ledger_sha256=PINS[LEDGER],
            active_creator_manifest={
                "path": NEW["creator"],
                "sha256": reference(repo / NEW["creator"])["manifest_sha256"],
            },
            measured_residual_target_singleton_ids=sorted(promoted_singletons),
            all_unselected_prior_status_objects_unchanged=True,
            unselected_prior_status_objects_count=4206 - len(promoted_singletons),
        )
    require(
        all(source_rows[sid]["source_status"] == "held" for sid in aliases),
        "Legacy alias ledger holds differ",
    )
    if promoted_singletons:
        write(output / "integrated_source_status.json", integrated)
    else:
        (output / "integrated_source_status.json").write_bytes(
            (repo / LEDGER).read_bytes()
        )
        require(
            sha((output / "integrated_source_status.json").read_bytes())
            == PINS[LEDGER],
            "Alias-only source ledger bytes changed",
        )
    projected = copy.deepcopy(historical)
    projected["historical_target_index_provenance"] = {
        key: copy.deepcopy(historical.get(key))
        for key in (
            "reviewed_at",
            "projection_reviewed_at",
            "class_assessment_reviewed_at",
            "measured_singleton_status_delta",
            "legacy_source_ledger_changed",
            "source_ledger_sha256",
            "fresh_class_assessment_performed",
            "class_artifacts_rebuilt",
        )
    }
    projected.pop("legacy_source_ledger_changed", None)
    projected.pop("class_assessment_reviewed_at", None)
    for row in projected["class_targets"]:
        cid = row["record_target_id"]
        if cid not in selected_classes:
            require(row == old_classes[cid], "Unselected historical class row changed")
            continue
        target = measured_classes[cid]
        path = (
            output / "class_payloads" / ("XMLCLASS-" + row["source_sha256"] + ".json")
        )
        write(path, target)
        for member in target["members"]:
            original_path = output / "originals" / member["source_filename"]
            original_path.parent.mkdir(exist_ok=True)
            original_path.write_bytes(
                (repo / "FGDC" / member["source_filename"]).read_bytes()
            )
            require(
                sha(original_path.read_bytes()) == member["source_sha256"],
                "Final class original differs",
            )
        row.update(
            source_semantic_status=target["source_semantic_status"],
            assessment_reviewed_at=reviewed_at,
            payload_path=str(path.relative_to(output)),
            payload_sha256=sha(path.read_bytes()),
            artifact_contract_sha256=target["artifact_contract"]["sha256"],
            member_assessments=target["member_assessments"],
            hold_reasons=target.get("hold_reasons", []),
        )
    for row in projected["singleton_targets"]:
        if row["record_target_id"] in promoted_singletons:
            row["source_semantic_status"] = "supported"
    count = Counter(
        row["source_semantic_status"]
        for row in projected["class_targets"] + projected["singleton_targets"]
    )
    promoted = len(promoted_classes) + len(promoted_singletons)
    require(
        count == {"supported": 3908 + promoted, "held": 64 - promoted, "failed": 6},
        "Target counts differ",
    )
    projected["summary"].update(
        source_supported_classes=204 + len(promoted_classes),
        source_held_classes=24 - len(promoted_classes),
        source_supported_targets=count["supported"],
        source_held_targets=count["held"],
        malformed_targets=6,
    )
    projected.update(
        kind="offline_record_target_finite_semantic_delta_projection",
        projection_reviewed_at=reviewed_at,
        reviewed_at=reviewed_at,
        frozen_source_ledger_modified=False,
        current_source_status_projection_changed=bool(promoted_singletons),
        measured_singleton_status_delta=[
            {"record_target_id": sid, **transition}
            for sid, transition in sorted(actual_singleton_transitions.items())
        ],
        class_assessment_scopes={
            "fresh_selected": {
                "reviewed_at": reviewed_at,
                "record_target_ids": sorted(selected_classes),
            },
            "unchanged_historical": {
                "reviewed_at": historical["class_assessment_reviewed_at"],
                "record_target_ids": sorted(set(old_classes) - set(selected_classes)),
                "artifact_resolver": {
                    "historical_index_path": TARGETS,
                    "historical_index_sha256": PINS[TARGETS],
                    "original_class_index_path": DOCS + "alias228_record_targets.json",
                    "original_class_index_sha256": "fd9bcba857c5d9816f44bbca0ac4c826c10527f64a7e6330468ee2fe814981d4",
                    "limit": "Retained historical payload paths and hashes resolve via the pinned prior index/measurement; those204 payloads were not copied or rebuilt in this output.",
                },
            },
        },
        source_to_target_index_unchanged=True,
        source_ledger_sha256=sha(
            (output / "integrated_source_status.json").read_bytes()
        ),
        historical_record_target_index_sha256=PINS[TARGETS],
        fresh_class_assessment_performed=True,
        class_artifacts_rebuilt=True,
        class_rows_source_index_and_payload_pins_unchanged=False,
        measured_class_target_ids=sorted(selected_classes),
        measured_singleton_ids=sorted(promoted_singletons),
        unselected_historical_class_rows_unchanged=True,
        all_class_uploads_remain_held=True,
        projection_scope="Only declared corrected classes and singletons are freshly measured. Unselected class rows retain their historical payload/contract pins; all source identities and provider holds remain intact.",
    )
    require(
        projected["source_to_target"] == historical["source_to_target"],
        "Source-to-target identities changed",
    )
    write(output / "record_target_delta_projection.json", projected)
    require(originals == inventory(repo), "An original XML changed")
    require(bindings == source_bindings(repo), "Runtime/test/contract input changed")
    actual = dict(guard.input_hashes)
    require(
        all(
            (
                originals[Path(p).stem]
                if p.startswith("FGDC/")
                else sha((repo / p).read_bytes())
            )
            == h
            for p, h in actual.items()
        ),
        "An actual repository input changed",
    )
    require(
        not any(guard.counts["tests"].values()) and not guard.blocked_call_sites,
        "Unexpected guarded I/O",
    )
    receipt = {
        "schema_version": 1,
        "status": "MEASURED_FINITE_SOURCE_AND_CLASS_SEMANTIC_DELTA",
        "base_main": BASE,
        "actual_checkout_revision": revision,
        "reviewed_at": reviewed_at,
        "helper_sha256": sha(Path(__file__).read_bytes()),
        "pinned_inputs_sha256": PINS,
        "profile_references": {axis: reference(repo / NEW[axis]) for axis in NEW},
        "candidate_ids_by_axis": {axis: sorted(sids) for axis, sids in ids.items()},
        "expected_class_transitions": EXPECTED_CLASS_TRANSITIONS,
        "actual_class_transitions": actual_transitions,
        "actual_singleton_transitions": actual_singleton_transitions,
        "source_counts": dict(source_counts),
        "target_summary": projected["summary"],
        "all4206_original_hashes_unchanged": True,
        "unselected_source_rows_unchanged": 4206 - len(promoted_singletons),
        "unselected_class_rows_unchanged": 228 - len(selected_classes),
        "all_class_uploads_held": True,
        "source_bindings_unchanged": True,
        "source_bindings_sha256": sha(canonical(bindings)),
        "actual_repository_inputs_sha256": actual,
        "guard": guard.counts,
        "unexpected_guard_events": guard.blocked_call_sites,
        "batches": batches,
        "rows": deltas,
        "provider_requests": 0,
        "new_release_grants": 0,
        "integrated_source_ledger": file_ref(
            output / "integrated_source_status.json", output
        ),
        "record_target_projection": file_ref(
            output / "record_target_delta_projection.json", output
        ),
    }
    write(output / "residual_target_validation.json", receipt)
    print(
        json.dumps(
            {
                "source_counts": dict(source_counts),
                "target_summary": projected["summary"],
                "receipt": str(output / "residual_target_validation.json"),
            }
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewed-at", required=True)
    args = parser.parse_args()
    os.environ.clear()
    sys.dont_write_bytecode = True
    repo, output = args.repo.resolve(), args.output.resolve()
    stamp = datetime.fromisoformat(args.reviewed_at.replace("Z", "+00:00"))
    require(
        stamp.utcoffset() is not None and stamp <= datetime.now(timezone.utc),
        "Explicit nonfuture aware review time required",
    )
    require(
        output.is_relative_to(Path("/tmp"))
        and output != Path("/tmp")
        and not output.is_relative_to(repo)
        and not output.exists()
        and output.parent.is_dir(),
        "Use a fresh /tmp output outside the repository",
    )
    require(
        sha((repo / "ci/run_offline_tests.py").read_bytes())
        == PINS["ci/run_offline_tests.py"],
        "Guard pin changed",
    )
    sys.path.insert(0, str(repo))
    from ci.run_offline_tests import OfflineGuard, checkout_revision, clean_environment

    revision = checkout_revision(repo)
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)

    class ReadBoundGuard(OfflineGuard):
        def __init__(self):
            super().__init__(repo, output, revision)
            self.input_hashes = {}
            self.hashing = False

        def check_read(self, target):
            super().check_read(target)
            if (
                not self.hashing
                and target.is_relative_to(repo)
                and target.is_file()
                and str(target.relative_to(repo)) not in self.input_hashes
            ):
                self.hashing = True
                try:
                    self.input_hashes[str(target.relative_to(repo))] = sha(
                        target.read_bytes()
                    )
                finally:
                    self.hashing = False

    guard = ReadBoundGuard()
    guard.library_files.add(Path(__file__).resolve())
    guard.install()
    guard.self_check()
    output.mkdir()
    validate(repo, output, args.reviewed_at, revision, guard)


if __name__ == "__main__":
    main()
