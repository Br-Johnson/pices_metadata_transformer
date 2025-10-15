#!/usr/bin/env python3
"""
Iteration orchestrator for the FGDC → Zenodo mapping feedback loop.

This helper script chains the sample-sized commands we run after UI spot checks:
1. Optionally back up the pre-filter list so the selected sample re-transforms.
2. Transform a limited batch of FGDC records.
3. Validate the regenerated Zenodo JSON.
4. Run the pre-upload duplicate check against the chosen Zenodo environment.
5. Verify uploads to confirm registry/log alignment.
6. Re-run metrics analysis to surface regressions.

The loop is designed to be repeatable while we tweak mapping logic.  It leaves a
succinct trail of reports under `output/reports/*/iteration_*` so the team can
compare runs or attach evidence to checklist updates.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from typing import List, Optional

# Allow relative imports from scripts/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger
from path_config import OutputPaths, default_log_dir


class IterationLoopRunner:
    """Coordinate the iterative test loop in a single command."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.logger = get_logger()
        self.paths = OutputPaths(args.output_dir)
        self.environment = "production" if args.production else "sandbox"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pre_filter_backup: Optional[str] = None

        # Report paths used by the downstream scripts.
        self.validation_report = os.path.join(
            self.paths.validation_reports_dir,
            f"iteration_validation_{self.timestamp}.json",
        )
        self.metrics_report = os.path.join(
            self.paths.metrics_reports_dir,
            f"iteration_metrics_{self.timestamp}.json",
        )
        self.verification_report = os.path.join(
            self.paths.verification_reports_dir,
            f"iteration_verification_{self.timestamp}.json",
        )

    # ------------------------------------------------------------------ helpers

    def _run_command(
        self,
        command: List[str],
        step_name: str,
        allow_nonzero: bool = False,
    ) -> bool:
        """Execute a subprocess command and surface concise output."""
        command_display = " ".join(command)
        print(f"\n[{step_name.upper()}] {command_display}")

        if self.args.dry_run:
            print("  (dry-run) command skipped")
            return True

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            if allow_nonzero:
                print(
                    f"  ⚠️  Step completed with exit code {result.returncode} "
                    f"(continuing due to allow_nonzero=True)"
                )
                if stdout:
                    print(f"  stdout:\n{stdout}")
                if stderr:
                    print(f"  stderr:\n{stderr}")
                return True

            print(f"  ❌ Command failed with exit code {result.returncode}")
            if stdout:
                print(f"  stdout:\n{stdout}")
            if stderr:
                print(f"  stderr:\n{stderr}")
            self.logger.log_error(
                "iteration_loop",
                step_name,
                "command_failed",
                stderr or stdout,
                "Subprocess returned zero exit status",
                command_display,
            )
            return False

        if stdout:
            preview = stdout if len(stdout) < 2000 else stdout[:2000] + "\n..."
            print(f"  stdout:\n{preview}")
        if stderr:
            print(f"  stderr:\n{stderr}")

        return True

    def _disable_prefilter(self):
        """Temporarily move the pre-filter list so samples re-transform."""
        if self.args.keep_prefilter:
            return

        pre_filter_path = self.paths.pre_filter_path
        if not os.path.exists(pre_filter_path):
            return

        backup_path = f"{pre_filter_path}.bak_{self.timestamp}"
        shutil.move(pre_filter_path, backup_path)
        self.pre_filter_backup = backup_path
        print(f"\n[SETUP] Backed up pre-filter list to {backup_path}")

    def _restore_prefilter(self):
        """Restore the pre-filter list if it was moved aside."""
        if self.args.keep_prefilter or not self.pre_filter_backup:
            return

        original_path = self.paths.pre_filter_path
        try:
            shutil.move(self.pre_filter_backup, original_path)
            print(f"\n[CLEANUP] Restored pre-filter list to {original_path}")
        except Exception as exc:
            print(
                f"\n[CLEANUP] ⚠️  Could not restore pre-filter file: {exc}\n"
                f"           Backup remains at {self.pre_filter_backup}"
            )
            self.logger.log_warning(
                "iteration_loop",
                "restore_prefilter",
                "restore_failed",
                str(exc),
                "Pre-filter file restored",
                f"Backup path: {self.pre_filter_backup}",
            )

    # ----------------------------------------------------------------- pipeline

    def run(self) -> bool:
        """Execute the full iteration loop."""
        if not self.args.dry_run:
            os.makedirs(os.path.dirname(self.validation_report), exist_ok=True)
            os.makedirs(os.path.dirname(self.metrics_report), exist_ok=True)
            os.makedirs(os.path.dirname(self.verification_report), exist_ok=True)

        success = True
        self._disable_prefilter()

        try:
            transform_cmd = [
                sys.executable,
                os.path.join("scripts", "batch_transform.py"),
                "--input",
                self.args.input_dir,
                "--output",
                self.args.output_dir,
                "--limit",
                str(self.args.limit),
                "--log-dir",
                self.args.transform_log_dir,
            ]
            success &= self._run_command(transform_cmd, "transform")
            if not success:
                return False

            if not self.args.skip_validation:
                validation_cmd = [
                    sys.executable,
                    os.path.join("scripts", "validate_zenodo.py"),
                    "--input",
                    self.paths.zenodo_json_dir,
                    "--output",
                    self.validation_report,
                    "--limit",
                    str(self.args.limit),
                    "--log-dir",
                    self.args.validation_log_dir,
                ]
                success &= self._run_command(validation_cmd, "validate")
                if not success and not self.args.continue_on_validation_failure:
                    return False

            if not self.args.skip_duplicates:
                duplicate_cmd = [
                    sys.executable,
                    os.path.join("scripts", "pre_upload_duplicate_check.py"),
                    "--output-dir",
                    self.args.output_dir,
                    "--limit",
                    str(self.args.limit),
                    "--log-dir",
                    self.args.duplicate_log_dir,
                ]
                duplicate_cmd.append("--production" if self.args.production else "--sandbox")
                success &= self._run_command(duplicate_cmd, "pre_upload_duplicate_check", allow_nonzero=True)

            if not self.args.skip_verification:
                verification_cmd = [
                    sys.executable,
                    os.path.join("scripts", "verify_uploads.py"),
                    "--output",
                    self.args.output_dir,
                    "--limit",
                    str(self.args.limit),
                    "--log-dir",
                    self.args.verification_log_dir,
                ]
                verification_cmd.append("--production" if self.args.production else "--sandbox")
                success &= self._run_command(verification_cmd, "verify_uploads")
                if success and not self.args.dry_run:
                    # The verification script writes to stdout; also record report path.
                    try:
                        with open(self.verification_report, "w") as handle:
                            handle.write(
                                f"Iteration verification executed at {self.timestamp}\n"
                                f"Command: {' '.join(verification_cmd)}\n"
                            )
                    except OSError as exc:
                        self.logger.log_warning(
                            "iteration_loop",
                            "write_verification_stub",
                            "write_failed",
                            str(exc),
                            "Verification stub written",
                            self.verification_report,
                        )

            if not self.args.skip_metrics:
                metrics_cmd = [
                    sys.executable,
                    os.path.join("scripts", "metrics_analysis.py"),
                    "--output-dir",
                    self.args.output_dir,
                    "--save-report",
                    "--report-file",
                    self.metrics_report,
                    "--log-dir",
                    self.args.metrics_log_dir,
                ]
                success &= self._run_command(metrics_cmd, "metrics_analysis")

            if self.args.reminder:
                print(
                    "\n[REMINDER] Review the latest Zenodo sandbox records via Playwright "
                    "and update docs/todo_list.md step 8 with observations."
                )

            return success

        finally:
            self._restore_prefilter()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the iterative mapping test loop prior to sandbox uploads.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-dir", default="FGDC", help="Directory containing FGDC XML files")
    parser.add_argument("--output-dir", default="output", help="Pipeline output directory")
    parser.add_argument("--limit", type=int, default=10, help="Number of records to process for the loop")
    parser.add_argument("--production", action="store_true", help="Use Zenodo production instead of sandbox")

    parser.add_argument("--skip-validation", action="store_true", help="Skip the validation step")
    parser.add_argument(
        "--continue-on-validation-failure",
        action="store_true",
        help="Continue the loop even if validation exits with errors",
    )
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip the duplicate check step")
    parser.add_argument("--skip-verification", action="store_true", help="Skip the upload verification step")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip metrics analysis")

    parser.add_argument(
        "--keep-prefilter",
        action="store_true",
        help="Do not move the pre-filter list aside before transforming",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them")
    parser.add_argument(
        "--reminder",
        action="store_true",
        help="Print a reminder to perform the manual Playwright spot check afterwards",
    )

    # Custom log directories (fall back to the shared defaults).
    parser.add_argument("--transform-log-dir", default=default_log_dir("transform"))
    parser.add_argument("--validation-log-dir", default=default_log_dir("validation"))
    parser.add_argument("--duplicate-log-dir", default=default_log_dir("pre_upload"))
    parser.add_argument("--verification-log-dir", default=default_log_dir("verification"))
    parser.add_argument("--metrics-log-dir", default=default_log_dir("metrics"))

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    runner = IterationLoopRunner(args)
    success = runner.run()
    if success:
        print("\n✅ Iteration loop completed. Review outputs under output/reports/* for details.")
        return 0
    print("\n❌ Iteration loop failed. Check logs above and in the logs/ directory.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
