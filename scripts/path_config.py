"""
Centralised helpers for managing the output directory structure.

This module normalises legacy paths into the new hierarchy:

output/
    data/
        zenodo_json/
        original_fgdc/
    reports/
        ...
    state/
        ...
    cache/

It also migrates files that used to live in the legacy flat structure so that
existing datasets continue to work after the reorganisation.
"""

import glob
import os
import shutil
from typing import Callable, Iterable, Optional


class OutputPaths:
    """Convenience wrapper for all output/state/report directories."""

    def __init__(self, base: str = "output"):
        self.base = base
        self.data_dir = os.path.join(base, "data")
        self.reports_dir = os.path.join(base, "reports")
        self.state_dir = os.path.join(base, "state")
        self.cache_dir = os.path.join(base, "cache")
        self.runtime_dir = os.path.join(base, "runtime")
        self._cache = {}

    # ------------------------------------------------------------------ helpers

    def _get_cached(self, key: str, builder: Callable[[], str]) -> str:
        if key not in self._cache:
            self._cache[key] = builder()
        return self._cache[key]

    @staticmethod
    def _ensure_parent(path: str):
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    def _prepare_dir(self, new_path: str, legacy_path: Optional[str] = None,
                     migrate_patterns: Optional[Iterable[str]] = None) -> str:
        if legacy_path and os.path.exists(legacy_path) and not os.path.exists(new_path):
            self._ensure_parent(new_path)
            shutil.move(legacy_path, new_path)
        os.makedirs(new_path, exist_ok=True)
        if migrate_patterns:
            self._migrate_patterns(migrate_patterns, new_path)
        return new_path

    def _prepare_file(self, new_path: str, legacy_path: Optional[str] = None) -> str:
        self._ensure_parent(new_path)
        if legacy_path and os.path.exists(legacy_path) and not os.path.exists(new_path):
            shutil.move(legacy_path, new_path)
        return new_path

    def _migrate_patterns(self, patterns: Iterable[str], destination: str):
        os.makedirs(destination, exist_ok=True)
        for pattern in patterns:
            for legacy_path in glob.glob(os.path.join(self.base, pattern)):
                target_path = os.path.join(destination, os.path.basename(legacy_path))
                if os.path.exists(target_path):
                    continue
                shutil.move(legacy_path, target_path)

    # ---------------------------------------------------------------- data dirs

    @property
    def zenodo_json_dir(self) -> str:
        return self._get_cached(
            "zenodo_json_dir",
            lambda: self._prepare_dir(
                os.path.join(self.data_dir, "zenodo_json"),
                legacy_path=os.path.join(self.base, "zenodo_json"),
            ),
        )

    @property
    def original_fgdc_dir(self) -> str:
        return self._get_cached(
            "original_fgdc_dir",
            lambda: self._prepare_dir(
                os.path.join(self.data_dir, "original_fgdc"),
                legacy_path=os.path.join(self.base, "original_fgdc"),
            ),
        )

    @property
    def cache_directory(self) -> str:
        return self._get_cached(
            "cache_directory",
            lambda: self._prepare_dir(self.cache_dir),
        )

    # --------------------------------------------------------------- report dirs

    @property
    def transform_reports_dir(self) -> str:
        return self._get_cached(
            "transform_reports_dir",
            lambda: self._prepare_dir(os.path.join(self.reports_dir, "transform")),
        )

    @property
    def validation_reports_dir(self) -> str:
        return self._get_cached(
            "validation_reports_dir",
            lambda: self._prepare_dir(os.path.join(self.reports_dir, "validation")),
        )

    @property
    def duplicates_reports_dir(self) -> str:
        return self._get_cached(
            "duplicates_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "duplicates"),
                migrate_patterns=["duplicate_check_report_*.txt"],
            ),
        )

    @property
    def pre_upload_reports_dir(self) -> str:
        return self._get_cached(
            "pre_upload_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "pre_upload"),
                migrate_patterns=["pre_upload_duplicate_check_*.json"],
            ),
        )

    @property
    def upload_reports_dir(self) -> str:
        return self._get_cached(
            "upload_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "uploads"),
                migrate_patterns=[
                    "batch_upload_log_*.json",
                    "batch_upload_errors_*.json",
                    "upload_audit_*.json",
                    "upload_errors.json",
                    "upload_report.txt",
                ],
            ),
        )

    @property
    def metrics_reports_dir(self) -> str:
        return self._get_cached(
            "metrics_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "metrics"),
                migrate_patterns=[
                    "enhanced_metrics_*.json",
                    "enhanced_metrics_analysis_*.json",
                ],
            ),
        )

    @property
    def verification_reports_dir(self) -> str:
        return self._get_cached(
            "verification_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "verification"),
                migrate_patterns=["verification_report.json", "verification_summary.txt"],
            ),
        )

    @property
    def publish_reports_dir(self) -> str:
        return self._get_cached(
            "publish_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "publish"),
                migrate_patterns=["publish_log.json", "publish_errors.json"],
            ),
        )

    @property
    def pipeline_reports_dir(self) -> str:
        return self._get_cached(
            "pipeline_reports_dir",
            lambda: self._prepare_dir(
                os.path.join(self.reports_dir, "pipeline"),
                migrate_patterns=["pipeline_summary_*.json", "field_analysis_summary.md"],
            ),
        )

    # --------------------------------------------------------------- state paths

    @property
    def uploads_state_dir(self) -> str:
        return self._get_cached(
            "uploads_state_dir",
            lambda: self._prepare_dir(os.path.join(self.state_dir, "uploads")),
        )

    @property
    def pre_upload_state_dir(self) -> str:
        return self._get_cached(
            "pre_upload_state_dir",
            lambda: self._prepare_dir(
                os.path.join(self.state_dir, "pre_upload"),
                migrate_patterns=[
                    "safe_to_upload.json",
                    "already_uploaded_to_zenodo.json",
                    "pre_filter_already_uploaded.json",
                ],
            ),
        )

    @property
    def pipeline_state_dir(self) -> str:
        return self._get_cached(
            "pipeline_state_dir",
            lambda: self._prepare_dir(
                os.path.join(self.state_dir, "pipeline"),
                migrate_patterns=["pipeline_state_*.json"],
            ),
        )

    @property
    def uploads_registry_path(self) -> str:
        return self._get_cached(
            "uploads_registry_path",
            lambda: self._prepare_file(
                os.path.join(self.uploads_state_dir, "uploads_registry.json"),
                legacy_path=os.path.join(self.base, "uploads_registry.json"),
            ),
        )

    @property
    def upload_log_path(self) -> str:
        return self._get_cached(
            "upload_log_path",
            lambda: self._prepare_file(
                os.path.join(self.uploads_state_dir, "upload_log.json"),
                legacy_path=os.path.join(self.base, "upload_log.json"),
            ),
        )

    @property
    def safe_to_upload_path(self) -> str:
        return self._get_cached(
            "safe_to_upload_path",
            lambda: self._prepare_file(
                os.path.join(self.pre_upload_state_dir, "safe_to_upload.json"),
                legacy_path=os.path.join(self.base, "safe_to_upload.json"),
            ),
        )

    @property
    def already_uploaded_path(self) -> str:
        return self._get_cached(
            "already_uploaded_path",
            lambda: self._prepare_file(
                os.path.join(self.pre_upload_state_dir, "already_uploaded_to_zenodo.json"),
                legacy_path=os.path.join(self.base, "already_uploaded_to_zenodo.json"),
            ),
        )

    @property
    def pre_filter_path(self) -> str:
        return self._get_cached(
            "pre_filter_path",
            lambda: self._prepare_file(
                os.path.join(self.pre_upload_state_dir, "pre_filter_already_uploaded.json"),
                legacy_path=os.path.join(self.base, "pre_filter_already_uploaded.json"),
            ),
        )

    def pipeline_state_path(self, environment: str) -> str:
        filename = f"pipeline_state_{environment}.json"
        legacy = os.path.join(self.base, filename)
        return self._prepare_file(os.path.join(self.pipeline_state_dir, filename), legacy)

    def pipeline_summary_path(self, environment: str) -> str:
        filename = f"pipeline_summary_{environment}.json"
        legacy = os.path.join(self.base, filename)
        return self._prepare_file(
            os.path.join(self.pipeline_reports_dir, filename),
            legacy_path=legacy,
        )

    def field_analysis_summary_path(self) -> str:
        legacy = os.path.join(self.base, "field_analysis_summary.md")
        return self._prepare_file(
            os.path.join(self.pipeline_reports_dir, "field_analysis_summary.md"),
            legacy_path=legacy,
        )

    # -------------------------------------------------------------- specific files

    @property
    def transform_summary_path(self) -> str:
        legacy = os.path.join(self.base, "transformation_summary.txt")
        return self._prepare_file(
            os.path.join(self.transform_reports_dir, "transformation_summary.txt"),
            legacy_path=legacy,
        )

    @property
    def validation_report_path(self) -> str:
        legacy = os.path.join(self.base, "validation_report.json")
        return self._prepare_file(
            os.path.join(self.validation_reports_dir, "validation_report.json"),
            legacy_path=legacy,
        )

    @property
    def verification_report_path(self) -> str:
        legacy = os.path.join(self.base, "verification_report.json")
        return self._prepare_file(
            os.path.join(self.verification_reports_dir, "verification_report.json"),
            legacy_path=legacy,
        )

    @property
    def verification_summary_path(self) -> str:
        legacy = os.path.join(self.base, "verification_summary.txt")
        return self._prepare_file(
            os.path.join(self.verification_reports_dir, "verification_summary.txt"),
            legacy_path=legacy,
        )

    @property
    def publish_log_path(self) -> str:
        legacy = os.path.join(self.base, "publish_log.json")
        return self._prepare_file(
            os.path.join(self.publish_reports_dir, "publish_log.json"),
            legacy_path=legacy,
        )

    @property
    def publish_errors_path(self) -> str:
        legacy = os.path.join(self.base, "publish_errors.json")
        return self._prepare_file(
            os.path.join(self.publish_reports_dir, "publish_errors.json"),
            legacy_path=legacy,
        )

    # ----------------------------------------------------------- convenience dirs

    def upload_batch_log_path(self, suffix: str) -> str:
        return os.path.join(self.upload_reports_dir, f"batch_upload_log_{suffix}.json")

    def upload_batch_errors_path(self, suffix: str) -> str:
        return os.path.join(self.upload_reports_dir, f"batch_upload_errors_{suffix}.json")

    def upload_audit_report_path(self, suffix: str) -> str:
        return os.path.join(self.upload_reports_dir, f"upload_audit_{suffix}.json")

    def enhanced_metrics_path(self, environment: str) -> str:
        return os.path.join(self.metrics_reports_dir, f"enhanced_metrics_{environment}.json")

    def enhanced_metrics_analysis_path(self, suffix: str) -> str:
        return os.path.join(self.metrics_reports_dir, f"enhanced_metrics_analysis_{suffix}.json")

    def duplicate_report_path(self, suffix: str) -> str:
        return os.path.join(self.duplicates_reports_dir, f"duplicate_check_report_{suffix}.txt")

    def pre_upload_report_path(self, suffix: str) -> str:
        return os.path.join(self.pre_upload_reports_dir, f"pre_upload_duplicate_check_{suffix}.json")

    def verification_report_output(self, suffix: str) -> str:
        return os.path.join(self.verification_reports_dir, f"verification_report_{suffix}.json")


def default_log_dir(name: str) -> str:
    """Return the default log directory for a given pipeline component."""
    directory = os.path.join("logs", name)
    os.makedirs(directory, exist_ok=True)
    return directory
