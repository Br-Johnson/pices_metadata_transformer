#!/usr/bin/env python3
"""
Comprehensive orchestration script for PICES FGDC to Zenodo migration pipeline.

This script runs the complete migration pipeline in logical order:
1. Transform FGDC XML files to Zenodo JSON
2. Validate transformed JSON for schema compliance
3. Pre-Upload Duplicate Check - Check for existing records on Zenodo
4. Upload to Zenodo (sandbox or production) - only safe-to-upload files
5. Post-upload duplicate verification against Zenodo
6. Generate audit reports and metrics
7. Verify uploads and data integrity
8. Generate comprehensive reports

Usage:
    python scripts/orchestrate_pipeline.py [options]

Options:
    --sandbox          Use Zenodo sandbox (default: True)
    --production       Use Zenodo production (overrides --sandbox)
    --interactive      Interactive mode: pause between major steps (default: False)
    --batch-size N     Upload batch size (default: 100)
    --limit N          Limit number of files to process (for testing)
    --skip-transform   Skip transformation step (assume already done)
    --skip-upload      Skip upload step (assume already done)
    --skip-validation  Skip validation step
    --skip-duplicates  Skip duplicate checking
    --skip-audit       Skip audit and metrics generation
    --output-dir DIR   Output directory (default: output)
    --resume           Resume from last successful step
    --dry-run          Show what would be done without executing
    --debug            Debug mode: verbose output, test with minimal data, validate all steps
"""

import os
import sys
import argparse
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger
from path_config import OutputPaths, default_log_dir


class PipelineOrchestrator:
    """Orchestrates the complete FGDC to Zenodo migration pipeline."""
    
    def __init__(self, args):
        self.args = args
        self.logger = get_logger()
        self.paths = OutputPaths(args.output_dir)
        self.start_time = datetime.now()
        self.pipeline_state = {
            'start_time': self.start_time.isoformat(),
            'steps_completed': [],
            'current_step': None,
            'errors': [],
            'warnings': [],
            'config': {
                'sandbox': args.sandbox,
                'production': args.production,
                'interactive': args.interactive,
                'batch_size': args.batch_size,
                'limit': args.limit,
                'output_dir': args.output_dir,
                'debug': getattr(args, 'debug', False),
                'replace_duplicates': getattr(args, 'replace_duplicates', False),
                'post_upload_dedupe': getattr(args, 'post_upload_dedupe', False),
            }
        }
        
        # Determine environment
        self.environment = "production" if args.production else "sandbox"
        self.pipeline_state['config']['environment'] = self.environment
        
        # Create state file path
        self.state_file = self.paths.pipeline_state_path(self.environment)
        
        # Load existing state if resuming
        if args.resume and os.path.exists(self.state_file):
            self._load_state()
    
    def _load_state(self):
        """Load pipeline state from file."""
        try:
            with open(self.state_file, 'r') as f:
                saved_state = json.load(f)
                self.pipeline_state.update(saved_state)
                self.logger.log_info(f"Resumed pipeline from state file: {self.state_file}")
                print(f"🔄 Resumed pipeline from previous run")
        except Exception as e:
            self.logger.log_error(
                "orchestrate",
                "load_state",
                "load_failed",
                str(e),
                "Pipeline state file parsed successfully",
                f"State file path: {self.state_file}",
                "Validate JSON structure or remove the corrupt state file before resuming"
            )
            print(f"⚠️  Could not load state file: {e}")
    
    def _save_state(self):
        """Save current pipeline state to file."""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.pipeline_state, f, indent=2)
        except Exception as e:
            self.logger.log_error(
                "orchestrate",
                "save_state",
                "save_failed",
                str(e),
                "Pipeline state persisted to disk",
                f"State file path: {self.state_file}",
                "Check filesystem permissions and available disk space"
            )
    
    def _run_command(self, command: List[str], description: str, step_name: str) -> bool:
        """Run a command and handle errors."""
        print(f"\n🔄 {description}...")
        self.pipeline_state['current_step'] = step_name
        
        if self.args.dry_run:
            print(f"   [DRY RUN] Would execute: {' '.join(command)}")
            return True
        
        # Debug mode: show command and add verbose output
        if getattr(self.args, 'debug', False):
            print(f"   [DEBUG] Executing: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Debug mode: show output
            if getattr(self.args, 'debug', False) and result.stdout:
                print(f"   [DEBUG] Output: {result.stdout[:500]}...")
            
            # Check if command succeeded
            if result.returncode == 0:
                print(f"✅ {description} completed successfully")
                self.pipeline_state['steps_completed'].append(step_name)
                self._save_state()
                return True
            else:
                # For validation steps, non-zero exit might be expected (validation issues found)
                if step_name == "validate":
                    print(f"⚠️  {description} completed with validation issues (exit code: {result.returncode})")
                    if result.stdout:
                        print(f"   Validation results: {result.stdout[:200]}...")
                    self.pipeline_state['steps_completed'].append(step_name)
                    self._save_state()
                    return True
                # For pre-upload duplicate check, non-zero exit means duplicates found (which is expected)
                elif step_name == "pre_upload_duplicate_check":
                    print(f"⚠️  {description} completed with duplicates found (exit code: {result.returncode})")
                    if result.stdout:
                        print(f"   Duplicate check results: {result.stdout[:200]}...")
                    self.pipeline_state['steps_completed'].append(step_name)
                    self._save_state()
                    return True
                else:
                    error_msg = f"Command failed with exit code {result.returncode}: {result.stderr}"
                    print(f"❌ {description} failed: {error_msg}")
                    
                    # Debug mode: show full error details
                    if getattr(self.args, 'debug', False):
                        print(f"   [DEBUG] Return code: {result.returncode}")
                        if result.stdout:
                            print(f"   [DEBUG] Stdout: {result.stdout}")
                        if result.stderr:
                            print(f"   [DEBUG] Stderr: {result.stderr}")
                    
                    self.pipeline_state['errors'].append({
                        'step': step_name,
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.logger.log_error("orchestrate", step_name, "command_failed", error_msg, "Successful command execution", "Review command output and fix issues")
                    return False
            
        except Exception as e:
            error_msg = f"Command execution error: {str(e)}"
            print(f"❌ {description} failed: {error_msg}")
            
            # Debug mode: show full error details
            if getattr(self.args, 'debug', False):
                print(f"   [DEBUG] Exception: {e}")
            
            self.pipeline_state['errors'].append({
                'step': step_name,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            self.logger.log_error("orchestrate", step_name, "command_failed", error_msg, "Successful command execution", "Review command output and fix issues")
            return False
    
    def _interactive_pause(self, step_name: str, description: str):
        """Pause for user interaction if in interactive mode."""
        if self.args.interactive:
            print(f"\n⏸️  INTERACTIVE PAUSE: {description}")
            print(f"   Step: {step_name}")
            print(f"   Environment: {self.environment}")
            print(f"   Completed steps: {', '.join(self.pipeline_state['steps_completed'])}")
            
            # Check if we're in a non-interactive environment (like CI/CD)
            if not sys.stdin.isatty():
                print("   [AUTO] Non-interactive environment detected, continuing automatically...")
                return True
            
            try:
                while True:
                    response = input("\n   Continue? (y/n/s for skip): ").lower().strip()
                    if response in ['y', 'yes']:
                        break
                    elif response in ['n', 'no']:
                        print("🛑 Pipeline stopped by user")
                        sys.exit(0)
                    elif response in ['s', 'skip']:
                        print(f"⏭️  Skipping {step_name}")
                        self.pipeline_state['steps_completed'].append(f"{step_name}_skipped")
                        self._save_state()
                        return False  # Return False to indicate step was skipped
                    else:
                        print("   Please enter 'y' (yes), 'n' (no), or 's' (skip)")
            except (EOFError, KeyboardInterrupt):
                print("\n   [AUTO] Input interrupted, continuing automatically...")
                return True
        
        return True
    
    def _check_prerequisites(self) -> bool:
        """Check prerequisites before starting pipeline."""
        print("🔍 Checking prerequisites...")
        
        # Check if .env file exists
        if not os.path.exists('.env'):
            print("❌ .env file not found. Please create it with your Zenodo API tokens.")
            if getattr(self.args, 'debug', False):
                print("   [DEBUG] Creating sample .env file for testing...")
                with open('.env', 'w') as f:
                    f.write("# Sample .env file for testing\n")
                    f.write("ZENODO_SANDBOX_TOKEN=your_sandbox_token_here\n")
                    f.write("ZENODO_PRODUCTION_TOKEN=your_production_token_here\n")
                print("   [DEBUG] Sample .env file created. Please add your actual tokens.")
            return False
        
        # Check if FGDC directory exists
        if not os.path.exists('FGDC'):
            print("❌ FGDC directory not found. Please ensure FGDC XML files are in the FGDC/ directory.")
            if getattr(self.args, 'debug', False):
                print("   [DEBUG] FGDC directory missing - this will cause issues in transform step")
            return False
        
        # Check if output directory exists or can be created
        try:
            os.makedirs(self.args.output_dir, exist_ok=True)
            if getattr(self.args, 'debug', False):
                print(f"   [DEBUG] Output directory: {self.args.output_dir}")
        except Exception as e:
            print(f"❌ Cannot create output directory {self.args.output_dir}: {e}")
            return False
        
        # Check if virtual environment is activated
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("⚠️  Virtual environment not detected. Consider activating venv.")
            if getattr(self.args, 'debug', False):
                print("   [DEBUG] Python path:", sys.prefix)
        
        # Check if required scripts exist and are executable
        required_scripts = [
            'scripts/batch_transform.py',
            'scripts/validate_zenodo.py',
            'scripts/pre_upload_duplicate_check.py',
            'scripts/batch_upload.py',
            'scripts/deduplicate_check.py',
            'scripts/upload_audit.py',
            'scripts/metrics_analysis.py',
            'scripts/enhanced_metrics.py',
            'scripts/verify_uploads.py'
        ]
        
        for script in required_scripts:
            if not os.path.exists(script):
                print(f"❌ Required script not found: {script}")
                return False
            if not os.access(script, os.R_OK):
                print(f"❌ Required script not readable: {script}")
                return False
            if getattr(self.args, 'debug', False):
                print(f"   [DEBUG] ✓ {script} exists and is readable")
        
        # Debug mode: additional checks
        if getattr(self.args, 'debug', False):
            print("   [DEBUG] Additional debug checks:")
            print(f"   [DEBUG] - Current working directory: {os.getcwd()}")
            print(f"   [DEBUG] - Python version: {sys.version}")
            print(f"   [DEBUG] - Environment: {self.environment}")
            print(f"   [DEBUG] - Batch size: {self.args.batch_size}")
            print(f"   [DEBUG] - Limit: {self.args.limit}")
            print(f"   [DEBUG] - Interactive: {self.args.interactive}")
            print(f"   [DEBUG] - Dry run: {self.args.dry_run}")
        
        print("✅ Prerequisites check passed")
        return True
    
    def step_transform(self) -> bool:
        """Step 1: Transform FGDC XML files to Zenodo JSON."""
        if self.args.skip_transform:
            print("⏭️  Skipping transformation step")
            return True
        
        if not self._interactive_pause("transform", "Transform FGDC XML files to Zenodo JSON"):
            return True
        
        # Check if transformations already exist
        zenodo_json_dir = self.paths.zenodo_json_dir
        if os.path.exists(zenodo_json_dir) and os.listdir(zenodo_json_dir):
            print(f"📁 Found existing transformed files in {zenodo_json_dir}")
            if self.args.interactive:
                response = input("   Transform anyway? (y/n): ").lower().strip()
                if response not in ['y', 'yes']:
                    print("⏭️  Skipping transformation step")
                    self.pipeline_state['steps_completed'].append('transform_skipped')
                    self._save_state()
                    return True
            else:
                print("   Proceeding with transformation (non-interactive mode)")
        
        command = [
            "python3", "scripts/batch_transform.py",
            "--input", "FGDC",
            "--output", self.args.output_dir
        ]
        
        if self.args.limit:
            command.extend(["--limit", str(self.args.limit)])
        
        return self._run_command(command, "Transforming FGDC XML files to Zenodo JSON", "transform")
    
    def step_validate(self) -> bool:
        """Step 2: Validate transformations."""
        if self.args.skip_validation:
            print("⏭️  Skipping validation step")
            return True
        
        if not self._interactive_pause("validate", "Validate transformed JSON files"):
            return True
        
        command = [
            "python3", "scripts/validate_zenodo.py",
            "--input", self.paths.zenodo_json_dir,
            "--output", self.paths.validation_report_path
        ]
        
        return self._run_command(command, "Validating transformed JSON files", "validate")
    
    def step_pre_upload_duplicate_check(self) -> bool:
        """Step 2: Check for duplicates on Zenodo before upload."""
        if not self._interactive_pause("pre_upload_duplicate_check", "Check for existing records on Zenodo"):
            return True
        
        command = [
            "python3", "scripts/pre_upload_duplicate_check.py",
            "--output-dir", self.args.output_dir,
        ]

        if self.args.production:
            command.append("--production")
        else:
            command.append("--sandbox")

        if getattr(self.args, 'replace_duplicates', False) and not self.args.production:
            command.append("--allow-replacements")

        if self.args.limit:
            command.extend(["--limit", str(self.args.limit)])

        return self._run_command(command, "Checking for existing records on Zenodo", "pre_upload_duplicate_check")
    
    def step_upload(self) -> bool:
        """Step 3: Upload files to Zenodo."""
        if self.args.skip_upload:
            print("⏭️  Skipping upload step")
            return True
        
        if not self._interactive_pause("upload", f"Upload files to Zenodo {self.environment}"):
            return True
        
        command = [
            "python3", "scripts/batch_upload.py",
            "--batch-size", str(self.args.batch_size),
            "--output-dir", self.args.output_dir
        ]
        
        if self.args.production:
            command.append("--production")
        else:
            command.append("--sandbox")
        
        if self.args.limit:
            command.extend(["--limit", str(self.args.limit)])

        if self.args.interactive:
            command.append("--interactive")

        if getattr(self.args, 'replace_duplicates', False) and not self.args.production:
            command.append("--replace-duplicates")

        return self._run_command(command, f"Uploading files to Zenodo {self.environment}", "upload")

    def step_check_duplicates(self) -> bool:
        """Step 5: Check for duplicates."""
        if self.args.skip_duplicates or not getattr(self.args, 'post_upload_dedupe', False):
            print("⏭️  Skipping duplicate check step")
            return True
        
        if not self._interactive_pause("duplicates", "Check for duplicate records"):
            return True
        
        command = [
            "python3", "scripts/deduplicate_check.py",
            "--output-dir", self.args.output_dir,
        ]
        
        if self.args.production:
            command.append("--production")
        else:
            command.append("--sandbox")
        
        return self._run_command(command, "Checking for duplicate records", "duplicates")
    
    def step_audit(self) -> bool:
        """Step 4: Generate audit reports and metrics."""
        if self.args.skip_audit:
            print("⏭️  Skipping audit step")
            return True
        
        if not self._interactive_pause("audit", "Generate audit reports and metrics"):
            return True
        
        # Run upload audit
        audit_command = [
            "python3", "scripts/upload_audit.py",
            "--output-dir", self.args.output_dir
        ]

        if not self._run_command(audit_command, "Generating upload audit report", "audit_upload"):
            return False
        
        # Run metrics analysis
        metrics_command = [
            "python3", "scripts/metrics_analysis.py",
            "--output-dir", self.args.output_dir,
            "--save-report"
        ]
        
        if not self._run_command(metrics_command, "Generating metrics analysis", "audit_metrics"):
            return False
        
        # Run enhanced metrics
        enhanced_command = [
            "python3", "scripts/enhanced_metrics.py",
            "--input", self.paths.zenodo_json_dir,
            "--output", self.paths.enhanced_metrics_path(self.environment)
        ]
        
        return self._run_command(enhanced_command, "Generating enhanced metrics", "audit_enhanced")
    
    def step_verify(self) -> bool:
        """Step 5: Verify uploads and data integrity."""
        if self.args.skip_verify:
            print("⏭️  Skipping verification step")
            return True
        
        if not self._interactive_pause("verify", "Verify uploads and data integrity"):
            return True
        
        command = [
            "python3", "scripts/verify_uploads.py",
            "--output", self.args.output_dir,
            "--log-dir", "logs"
        ]
        
        if self.args.production:
            command.append("--production")
        else:
            command.append("--sandbox")
        
        return self._run_command(command, "Verifying uploads and data integrity", "verify")
    
    def step_generate_reports(self) -> bool:
        """Step 6: Generate comprehensive final reports."""
        if self.args.skip_reports:
            print("⏭️  Skipping final report generation")
            return True
        
        if not self._interactive_pause("reports", "Generate comprehensive final reports"):
            return True
        
        print("\n📊 Generating comprehensive final reports...")
        
        # Generate pipeline summary
        self._generate_pipeline_summary()
        
        # Generate field analysis summary if it doesn't exist
        field_analysis_path = self.paths.field_analysis_summary_path()
        if not os.path.exists(field_analysis_path):
            print("📋 Generating field analysis summary...")
            # This would typically call a field analysis script if it exists
        
        print("✅ Final reports generated")
        self.pipeline_state['steps_completed'].append("reports")
        self._save_state()
        return True
    
    def _generate_pipeline_summary(self):
        """Generate a comprehensive pipeline summary report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        summary = {
            'pipeline_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'duration_human': str(duration),
                'environment': self.environment,
                'steps_completed': self.pipeline_state['steps_completed'],
                'errors': self.pipeline_state['errors'],
                'warnings': self.pipeline_state['warnings'],
                'configuration': self.pipeline_state['config']
            }
        }
        
        # Save summary
        summary_file = self.paths.pipeline_summary_path(self.environment)
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary to console
        print(f"\n{'='*80}")
        print(f"PIPELINE SUMMARY - {self.environment.upper()}")
        print(f"{'='*80}")
        print(f"Duration: {duration}")
        print(f"Environment: {self.environment}")
        print(f"Steps completed: {len(self.pipeline_state['steps_completed'])}")
        print(f"Errors: {len(self.pipeline_state['errors'])}")
        print(f"Warnings: {len(self.pipeline_state['warnings'])}")
        print(f"Summary saved to: {summary_file}")
        
        if self.pipeline_state['errors']:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for error in self.pipeline_state['errors']:
                print(f"   - {error['step']}: {error['error']}")
        
        if self.pipeline_state['warnings']:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.pipeline_state['warnings']:
                print(f"   - {warning}")
    
    def run_pipeline(self) -> bool:
        """Run the complete pipeline."""
        print(f"🚀 Starting PICES FGDC to Zenodo Migration Pipeline")
        print(f"   Environment: {self.environment}")
        print(f"   Interactive: {self.args.interactive}")
        print(f"   Batch size: {self.args.batch_size}")
        print(f"   Output directory: {self.args.output_dir}")
        if self.args.limit:
            print(f"   Limit: {self.args.limit} files")
        if getattr(self.args, 'replace_duplicates', False):
            print("   Duplicate replacements: ENABLED (sandbox only)")
        else:
            print("   Duplicate replacements: disabled")
        print(
            "   Post-upload deduplicate check: "
            + ("ENABLED" if getattr(self.args, 'post_upload_dedupe', False) else "skipped by default")
        )
        print(f"{'='*80}")
        
        # Check prerequisites
        if not self._check_prerequisites():
            return False
        
        # Run pipeline steps
        steps = [
            ("Transform", self.step_transform),
            ("Validate", self.step_validate),
            ("Pre-Upload Duplicate Check", self.step_pre_upload_duplicate_check),
            ("Upload", self.step_upload),
            ("Check Duplicates", self.step_check_duplicates),
            ("Audit", self.step_audit),
            ("Verify", self.step_verify),
            ("Generate Reports", self.step_generate_reports)
        ]
        
        for step_name, step_func in steps:
            print(f"\n{'='*60}")
            print(f"STEP: {step_name}")
            print(f"{'='*60}")
            
            # Check if step was already completed or skipped
            if step_name.lower().replace(' ', '_') in [s.replace('_skipped', '') for s in self.pipeline_state['steps_completed']]:
                print(f"⏭️  Step {step_name} already completed or skipped")
                continue
            
            if not step_func():
                print(f"❌ Pipeline failed at step: {step_name}")
                return False
        
        print(f"\n🎉 Pipeline completed successfully!")
        return True


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Comprehensive orchestration script for PICES FGDC to Zenodo migration pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline in sandbox (default)
  python scripts/orchestrate_pipeline.py

  # Run in production with interactive mode
  python scripts/orchestrate_pipeline.py --production --interactive

  # Test with limited files
  python scripts/orchestrate_pipeline.py --limit 10 --interactive

  # Resume from previous run
  python scripts/orchestrate_pipeline.py --resume

  # Dry run to see what would be executed
  python scripts/orchestrate_pipeline.py --dry-run

  # Debug mode for testing
  python scripts/orchestrate_pipeline.py --debug --limit 5 --interactive
        """
    )
    
    # Environment options
    parser.add_argument('--sandbox', action='store_true', default=True,
                       help='Use Zenodo sandbox (default: True)')
    parser.add_argument('--production', action='store_true',
                       help='Use Zenodo production (overrides --sandbox)')
    
    # Mode options
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive mode: pause between major steps (default: False)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    parser.add_argument('--debug', action='store_true',
                       help='Debug mode: verbose output, test with minimal data, validate all steps')
    
    # Processing options
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Upload batch size (default: 100)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of files to process (for testing)')
    parser.add_argument('--output-dir', default='output',
                       help='Output directory (default: output)')
    parser.add_argument('--replace-duplicates', action='store_true',
                       help='Sandbox only: replace duplicates using pre-upload replacement plan')

    # Skip options
    parser.add_argument('--skip-transform', action='store_true',
                       help='Skip transformation step (assume already done)')
    parser.add_argument('--skip-upload', action='store_true',
                       help='Skip upload step (assume already done)')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip validation step')
    parser.add_argument('--skip-duplicates', action='store_true',
                       help='Skip duplicate checking')
    parser.add_argument('--post-upload-dedupe', action='store_true',
                        help='Run the post-upload duplicate check step')
    parser.add_argument('--skip-audit', action='store_true',
                       help='Skip audit and metrics generation')
    parser.add_argument('--skip-verify', action='store_true',
                       help='Skip verification step')
    parser.add_argument('--skip-reports', action='store_true',
                       help='Skip final report generation')
    
    # Resume option
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last successful step')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.production and args.sandbox:
        print("❌ Cannot specify both --production and --sandbox")
        sys.exit(1)
    
    if args.batch_size <= 0:
        print("❌ Batch size must be positive")
        sys.exit(1)

    if args.limit and args.limit <= 0:
        print("❌ Limit must be positive")
        sys.exit(1)

    if args.replace_duplicates and args.production:
        print("❌ Duplicate replacement is restricted to sandbox runs. Remove --replace-duplicates for production uploads.")
        sys.exit(1)
    
    # Initialize logger early
    from logger import initialize_logger
    initialize_logger(default_log_dir("orchestrator"))
    
    # Debug mode adjustments
    if args.debug:
        print("🐛 DEBUG MODE ENABLED")
        print("   - Setting limit to 5 files for testing")
        print("   - Enabling interactive mode")
        print("   - Enabling verbose output")
        args.limit = 5
        args.interactive = True
        args.batch_size = 2  # Small batch size for testing
    
    # Create orchestrator and run pipeline
    orchestrator = PipelineOrchestrator(args)
    
    try:
        success = orchestrator.run_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted by user")
        orchestrator._save_state()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed with unexpected error: {e}")
        orchestrator.logger.log_error("orchestrate", "main", "unexpected_error", str(e), "Successful execution", "Review error details and fix issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
