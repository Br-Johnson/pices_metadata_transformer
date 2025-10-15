"""Generate Plan B JSON-LD records for ODIS harvesting."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dto import CanonicalRecordDTO, load_dto
from scripts.logger import get_logger, initialize_logger
from scripts.path_config import OutputPaths, default_log_dir


LICENSE_MAP = {
    "cc-zero": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def infer_zenodo_id(dto: CanonicalRecordDTO) -> str:
    metadata = dto.zenodo_metadata
    doi = metadata.get("doi") or metadata.get("preres")
    if isinstance(doi, str) and doi:
        return doi.rsplit("/", 1)[-1]
    deposition_id = dto.extra_metadata.get("deposition_id") if isinstance(dto.extra_metadata, dict) else None
    if deposition_id:
        return str(deposition_id)
    return dto.fgdc_id


def build_jsonld(dto: CanonicalRecordDTO, record_url: str) -> Dict[str, object]:
    metadata = dto.zenodo_metadata
    identifier_list: List[str] = []
    if metadata.get("doi"):
        identifier_list.append(metadata["doi"])
    if metadata.get("preres") and metadata["preres"] not in identifier_list:
        identifier_list.append(metadata["preres"])

    related = [link.identifier for link in dto.bibliographic_links if link.identifier]
    for identifier in related:
        if identifier not in identifier_list:
            identifier_list.append(identifier)

    creators_payload: List[Dict[str, str]] = []
    for creator in metadata.get("creators", []):
        name = creator.get("name")
        if not name:
            continue
        creators_payload.append({"@type": "Person", "name": name})

    keywords = metadata.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]

    doi = metadata.get("doi")
    landing_page = None
    if isinstance(doi, str) and doi:
        suffix = doi.split("doi.org/")[-1] if "doi.org/" in doi else doi
        landing_page = f"https://doi.org/{suffix}"

    jsonld = {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "@id": record_url,
        "name": metadata.get("title"),
        "description": metadata.get("description"),
        "identifier": identifier_list,
        "url": landing_page or metadata.get("notes"),
        "creator": creators_payload,
        "publisher": {
            "@type": "Organization",
            "name": metadata.get("publisher"),
        },
        "datePublished": metadata.get("publication_date"),
        "keywords": keywords,
    }

    license_key = metadata.get("license")
    if license_key in LICENSE_MAP:
        jsonld["license"] = LICENSE_MAP[license_key]

    if related:
        jsonld["sameAs"] = related

    return jsonld


def write_jsonld(dto: CanonicalRecordDTO, output_dir: Path, base_url: str) -> Path:
    zenodo_id = infer_zenodo_id(dto)
    filename = f"{zenodo_id}.jsonld"
    record_url = f"{base_url.rstrip('/')}/{filename}"
    jsonld_payload = build_jsonld(dto, record_url)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(jsonld_payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def build_sitemap(paths: Iterable[Path], base_url: str, sitemap_path: Path) -> None:
    sitemap_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
    for path in sorted(paths):
        loc = f"{base_url.rstrip('/')}/{path.name}"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{now}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    sitemap_path.write_text("\n".join(lines), encoding="utf-8")


def validate_records(records: Iterable[Path]) -> Dict[str, object]:
    failures: List[str] = []
    record_list = list(records)
    for record in record_list:
        try:
            payload = json.loads(record.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"{record.name}: {exc}")
            continue
        for field in ("@context", "@type", "name"):
            if not payload.get(field):
                failures.append(f"{record.name}: missing {field}")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": len(record_list),
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate JSON-LD catalogue")
    parser.add_argument("--dto-dir", default="output/data/dto", help="Directory containing DTO files")
    parser.add_argument("--output-dir", default="docs/odc/records", help="Destination for JSON-LD files")
    parser.add_argument("--sitemap", default="docs/odc/sitemap.xml", help="Sitemap output path")
    parser.add_argument("--base-url", default="https://pices-data.github.io/pices-metadata-transformer/odc/records", help="Base URL for published JSON-LD")
    parser.add_argument("--limit", type=int, help="Limit number of DTO records to process")
    parser.add_argument("--log-dir", default=default_log_dir("jsonld"), help="Log directory")

    args = parser.parse_args()

    initialize_logger(args.log_dir)
    logger = get_logger()
    paths = OutputPaths("output")

    dto_dir = Path(args.dto_dir)
    output_dir = Path(args.output_dir)
    sitemap_path = Path(args.sitemap)

    dto_files = sorted(dto_dir.glob("*.json"))
    if args.limit is not None:
        dto_files = dto_files[: args.limit]

    generated_files: List[Path] = []
    for dto_file in dto_files:
        dto = load_dto(str(dto_file))
        generated_files.append(write_jsonld(dto, output_dir, args.base_url))

    build_sitemap(generated_files, args.base_url, sitemap_path)

    odc_reports = Path(paths.odc_reports_dir)
    odc_reports.mkdir(parents=True, exist_ok=True)
    health_path = odc_reports / "harvest_status.json"
    health = validate_records(generated_files)
    with open(health_path, "w", encoding="utf-8") as handle:
        json.dump(health, handle, indent=2, ensure_ascii=False)

    logger.log_info(
        f"Generated {len(generated_files)} JSON-LD records at {output_dir}; sitemap at {sitemap_path}"
    )


if __name__ == "__main__":
    main()

