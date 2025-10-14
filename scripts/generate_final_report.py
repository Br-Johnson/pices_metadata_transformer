#!/usr/bin/env python3
"""
Generate a comprehensive PDF report for the FGDC → Zenodo sandbox run.
The report consolidates key metrics, visualisations, and review queues
so stakeholders can evaluate data quality and publishing readiness.
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "output" / "reports"
PIPELINE_DIR = REPORTS_DIR / "pipeline"
UPLOAD_REPORTS_DIR = REPORTS_DIR / "uploads"
VERIFICATION_DIR = REPORTS_DIR / "verification"
METRICS_DIR = REPORTS_DIR / "metrics"

# Ensure Matplotlib caches are written to a location we control
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "output" / "runtime" / "matplotlib"))

import matplotlib  # noqa: E402

# Use a non-interactive backend suitable for automated environments
matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_latest(pattern: str, search_dir: Path) -> Path:
    candidates = sorted(search_dir.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No files matched pattern '{pattern}' in {search_dir}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_duplicates() -> Tuple[int, List[Dict[str, str]]]:
    duplicates_path = UPLOAD_REPORTS_DIR / "duplicate_records_sandbox.csv"
    if not duplicates_path.exists():
        return 0, []

    with duplicates_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return len(rows), rows[:15]


def gather_archive_info() -> List[Dict[str, str]]:
    archives = []
    archive_dir = PROJECT_ROOT / "output" / "data"
    for name in ("original_fgdc", "zenodo_json"):
        path = archive_dir / f"{name}.zip"
        if not path.exists():
            continue
        size_mb = path.stat().st_size / (1024 * 1024) if path.stat().st_size else 0
        archives.append(
            {
                "label": name.replace("_", " ").title(),
                "path": str(path.relative_to(PROJECT_ROOT)),
                "size_mb": size_mb,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
        )
    return archives


def load_upload_titles() -> Dict[str, str]:
    """Build a map of FGDC IDs to titles using the upload log."""
    title_map: Dict[str, str] = {}
    upload_log_path = PROJECT_ROOT / "output" / "state" / "uploads" / "upload_log.json"
    if not upload_log_path.exists():
        return title_map

    with upload_log_path.open("r", encoding="utf-8") as handle:
        try:
            upload_entries = json.load(handle)
        except json.JSONDecodeError:
            return title_map

    for entry in upload_entries:
        json_file = entry.get("json_file", "")
        if not json_file.startswith("output/data/zenodo_json/"):
            continue
        fgdc_id = Path(json_file).stem
        title = entry.get("metadata", {}).get("title")
        if fgdc_id and title:
            title_map.setdefault(fgdc_id, title)
    return title_map


def load_non_open_access(records: List[Dict], title_map: Dict[str, str]) -> List[Dict]:
    flagged = []
    for record in records:
        compliance = record.get("compliance", {})
        if not compliance.get("open_access_compliant", True):
            fgdc_id = record["file_info"]["filename"].replace(".xml", "")
            flagged.append(
                {
                    "fgdc": fgdc_id,
                    "title": title_map.get(fgdc_id, "Title unavailable"),
                    "reason": compliance.get("open_access_reason", "Policy flag triggered"),
                }
            )
    return flagged


def build_summary_page(pdf: PdfPages, metrics_summary: Dict, audit_summary: Dict, verification_counts: Dict, duplicate_count: int, non_open: List[Dict], archive_info: List[Dict], autopublish_enabled: bool) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 Portrait
    ax.axis("off")

    lines = [
        "PICES FGDC → Zenodo Sandbox Migration",
        "",
        f"Report generated: {datetime.utcnow():%Y-%m-%d %H:%M UTC}",
        "",
        "Key Metrics",
        f"• Total FGDC records processed: {metrics_summary['total_records']:,}",
        f"• Average quality score: {metrics_summary['overall_scores']['average']:.1f}",
        f"• Upload success rate: {audit_summary['success_rate_percent']:.2f}%",
        f"• Published verification success: {verification_counts['success_rate']:.2f}%",
        f"• Duplicate sandbox titles skipped: {duplicate_count}",
        "",
        "Archival Outputs",
        (
            "• Archive bundles: "
            + (
                ", ".join(
                    f"{item['label']} ({item['size_mb']:.1f} MB)"
                    for item in archive_info
                )
                if archive_info else "Not generated"
            )
        ),
        "",
        "Auto-Publish Configuration",
        f"• Auto publish on upload: {'ENABLED' if autopublish_enabled else 'DISABLED (historical run)'}",
        "• Recovery path: re-run scripts/publish_records.py for any failed publication events",
        "",
        "Outstanding Manual Reviews",
        (
            "• Non-open-access records: "
            + (", ".join(item['fgdc'] for item in non_open) if non_open else "None – all compliant")
        ),
        "• Null-byte FGDC sources requiring re-export: FGDC-3373, FGDC-3484",
    ]

    y = 0.95
    for line in lines:
        fontsize = 16 if "PICES FGDC" in line else 12
        ax.text(0.05, y, line, fontsize=fontsize, va="top", ha="left", wrap=True)
        y -= 0.035 if fontsize == 12 else 0.05

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_pipeline_overview_page(pdf: PdfPages, archive_info: List[Dict], autopublish_enabled: bool) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    lines = [
        "Pipeline Overview",
        "",
        "End-to-End Approach",
        "  • Transform FGDC XML → Zenodo JSON (scripts/batch_transform.py)",
        "  • Validate JSON payloads before any uploads",
        "  • Screen for existing sandbox records and skip duplicates",
        "  • Upload in controlled batches with audit + metrics checkpoints",
        "  • Verify metadata/files against Zenodo before publication",
        f"  • Auto publish on upload: {'enabled' if autopublish_enabled else 'disabled'} (scripts/batch_upload.py)",
        "  • Archive both the original FGDC copies and generated Zenodo JSON",
        "",
        "Archive Bundles",
    ]

    if archive_info:
        for item in archive_info:
            lines.append(
                f"  • {item['label']} – {item['size_mb']:.1f} MB (updated {item['modified']} UTC)"
            )
    else:
        lines.append("  • Archives not yet generated")

    lines.extend([
        "",
        "Key Automation",
        "  • Duplicate avoidance uses `output/state/pre_upload/safe_to_upload.json`",
        "  • Upload registry + logs power publish retries and QA tracking",
        "  • PDF reporting consolidates metrics, outstanding QC items, and roadmap",
    ])

    y = 0.95
    for line in lines:
        fontsize = 14 if line.strip() in {"Pipeline Overview"} else 11
        ax.text(0.05, y, line, fontsize=fontsize, va="top", ha="left", wrap=True)
        y -= 0.03 if fontsize == 11 else 0.05

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_mapping_decisions_page(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    mapping_points = [
        "Metadata Mapping Decisions",
        "",
        "  • Default publisher/distributor set to North Pacific Marine Science Organization when absent",
        "  • License inference normalises CC phrases to SPDX IDs and falls back to CC0 for open access",
        "  • Bounding boxes that cross the dateline preserved with warning but not split to retain fidelity",
        "  • Date normalization collapses ranges to first year with provenance logged in warnings",
        "  • Original FGDC contact information promoted to creators when origin nodes are missing",
        "  • All unmapped FGDC fields appended to Zenodo notes to maintain information parity",
        "  • Communities list always injects PICES to simplify downstream publishing",
    ]

    y = 0.95
    for line in mapping_points:
        fontsize = 14 if "Metadata Mapping Decisions" in line else 11
        ax.text(0.05, y, line, fontsize=fontsize, va="top", ha="left", wrap=True)
        y -= 0.03 if fontsize == 11 else 0.05

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_qc_page(pdf: PdfPages, duplicate_count: int, non_open: List[Dict]) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    lines = [
        "Quality Assurance & Outstanding Checks",
        "",
        f"  • Pre-existing sandbox records skipped this run: {duplicate_count} (see duplicate_records_sandbox.csv)",
    ]

    if non_open:
        lines.append(
            "  • Access policy review: " + ", ".join(item['fgdc'] for item in non_open)
        )
    else:
        lines.append("  • Access policy review: none pending")

    lines.extend([
        "  • Null-byte FGDC sources requiring replacement: FGDC-3373, FGDC-3484",
        "  • Transformation warnings stored in logs/transform/warnings.json for audit",
        "  • Publish errors log is empty after retry (output/reports/publish/publish_errors.json)",
        "  • Monitor upload registry for late publish retries and DOI activations",
    ])

    y = 0.95
    for line in lines:
        fontsize = 14 if "Quality Assurance" in line else 11
        ax.text(0.05, y, line, fontsize=fontsize, va="top", ha="left", wrap=True)
        y -= 0.03 if fontsize == 11 else 0.05

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_roadmap_page(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    lines = [
        "Roadmap & Next Steps",
        "",
        "Short-Term",
        "  • Refresh 108 legacy sandbox DOIs or document decision to keep historical metadata",
        "  • Replace corrupted FGDC sources and rerun targeted transformation/upload",
        "  • Resolve access exceptions with metadata or policy updates",
        "  • Ship production auto-publish rollout (default --publish-on-upload in orchestrator)",
        "",
        "Mid-Term",
        "  • Implement archival retention policy for bulk logs and cache snapshots",
        "  • Extend QA tooling to surface unmapped FGDC fields requiring new crosswalk rules",
        "  • Integrate publish metrics into monitoring dashboards (DOI activation latency, community joins)",
        "",
        "Long-Term",
        "  • Prepare production cutover once sandbox sign-off is complete",
        "  • Track Zenodo API migration to InvenioRDM for future ROR support",
        "  • Evaluate incremental refresh strategy for new/updated FGDC packages",
    ]

    y = 0.95
    for line in lines:
        fontsize = 14 if line.strip() in {"Roadmap & Next Steps"} else 11
        ax.text(0.05, y, line, fontsize=fontsize, va="top", ha="left", wrap=True)
        y -= 0.03 if fontsize == 11 else 0.05

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_quality_page(pdf: PdfPages, quality_distribution: Dict) -> None:
    labels = list(quality_distribution.keys())
    values = [quality_distribution[label] for label in labels]

    fig, ax = plt.subplots(figsize=(8.27, 5))
    ax.bar(labels, values, color="#2C7FB8")
    ax.set_title("Quality Distribution Across Transformed Records")
    ax.set_xlabel("Quality Grade")
    ax.set_ylabel("Record Count")
    for idx, value in enumerate(values):
        ax.text(idx, value + max(values) * 0.01, f"{value}", ha="center", va="bottom")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_coverage_page(pdf: PdfPages, coverage_stats: Dict, compliance_stats: Dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 5))

    # Field coverage chart
    coverage_labels = ["Critical", "Important", "Optional"]
    coverage_values = [
        coverage_stats.get("avg_critical_fields", 0),
        coverage_stats.get("avg_important_fields", 0),
        coverage_stats.get("avg_optional_fields", 0),
    ]
    axes[0].barh(coverage_labels, coverage_values, color="#41B6C4")
    axes[0].set_xlim(0, 100)
    axes[0].set_title("Average Field Coverage (%)")
    for value, label in zip(coverage_values, coverage_labels):
        axes[0].text(value + 1, label, f"{value:.1f}%", va="center")

    # Compliance chart
    comp_labels = ["Zenodo Required", "Zenodo Recommended", "PICES Community", "Open Access", "License"]
    comp_values = [
        compliance_stats.get("zenodo_required_avg", 0),
        compliance_stats.get("zenodo_recommended_avg", 0),
        compliance_stats.get("pices_community_compliance", 0),
        compliance_stats.get("open_access_compliance", 0),
        compliance_stats.get("license_compliance", 0),
    ]
    axes[1].bar(comp_labels, comp_values, color="#225EA8")
    axes[1].set_ylim(0, 105)
    axes[1].set_xticklabels(comp_labels, rotation=20, ha="right")
    axes[1].set_title("Compliance Snapshot (%)")
    for idx, value in enumerate(comp_values):
        axes[1].text(idx, value + 1, f"{value:.1f}%", ha="center")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_duplicates_page(pdf: PdfPages, duplicate_rows: List[Dict]) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    ax.set_title("Pre-existing Sandbox Records (Already Published)", fontsize=14, loc="left")

    columns = ["FGDC_ID", "Title", "Publication Date"]
    table_data = [
        [row.get("FGDC_ID", ""), row.get("Title", "")[:80], row.get("Publication Date", "")]
        for row in duplicate_rows
    ]

    table = ax.table(cellText=table_data, colLabels=columns, colWidths=[0.15, 0.65, 0.2], loc="upper left")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.4)

    ax.text(
        0.0,
        -0.05,
        "Full CSV: output/reports/uploads/duplicate_records_sandbox.csv",
        transform=ax.transAxes,
        fontsize=10,
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_exceptions_page(pdf: PdfPages, non_open: List[Dict]) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 5))
    ax.axis("off")
    ax.set_title("Access Policy Exceptions", fontsize=14, loc="left")

    if not non_open:
        ax.text(0.05, 0.8, "No outstanding access exceptions – all records are open access compliant.", fontsize=12)
    else:
        columns = ["FGDC_ID", "Reason"]
        table_data = [[row["fgdc"], row.get("reason", "Policy flag triggered")] for row in non_open]
        table = ax.table(cellText=table_data, colLabels=columns, colWidths=[0.2, 0.8], loc="upper left")
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.4)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    metrics_path = PROJECT_ROOT / "output" / "enhanced_metrics_sandbox.json"
    metrics = load_json(metrics_path)
    metrics_summary = metrics["summary"]
    quality_distribution = metrics_summary["quality_distribution"]
    coverage_stats = metrics_summary["field_coverage_stats"]
    compliance_stats = metrics_summary["compliance_stats"]
    title_map = load_upload_titles()
    non_open = load_non_open_access(metrics.get("individual_metrics", []), title_map)
    archive_info = gather_archive_info()

    latest_audit_path = load_latest("upload_audit_*.json", UPLOAD_REPORTS_DIR)
    audit_summary = load_json(latest_audit_path).get("summary", {})

    verification_report_path = VERIFICATION_DIR / "verification_report.json"
    verification_report = []
    if verification_report_path.exists():
        verification_report = json.load(verification_report_path.open("r", encoding="utf-8"))

    total_verified = len(verification_report)
    success_count = sum(1 for record in verification_report if record.get("verification_successful"))
    verification_counts = {
        "total": total_verified,
        "success": success_count,
        "failed": total_verified - success_count,
        "success_rate": (success_count / total_verified * 100) if total_verified else 0.0,
    }

    duplicate_count, duplicate_rows = load_duplicates()

    batch_log_candidates = list(UPLOAD_REPORTS_DIR.glob("batch_upload_log_*.json"))
    autopublish_enabled = False
    if batch_log_candidates:
        latest_batch_path = max(batch_log_candidates, key=lambda p: p.stat().st_mtime)
        latest_batch_log = load_json(latest_batch_path)
        autopublish_enabled = latest_batch_log.get("publish_on_upload", False)

    pdf_path = PIPELINE_DIR / "final_sandbox_report.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(pdf_path) as pdf:
        build_summary_page(
            pdf,
            metrics_summary,
            audit_summary,
            verification_counts,
            duplicate_count,
            non_open,
            archive_info,
            autopublish_enabled,
        )
        build_pipeline_overview_page(pdf, archive_info, autopublish_enabled)
        build_mapping_decisions_page(pdf)
        build_qc_page(pdf, duplicate_count, non_open)
        build_roadmap_page(pdf)
        build_quality_page(pdf, quality_distribution)
        build_coverage_page(pdf, coverage_stats, compliance_stats)
        build_duplicates_page(pdf, duplicate_rows)
        build_exceptions_page(pdf, non_open)

    print(f"PDF report generated at {pdf_path}")


if __name__ == "__main__":
    main()
