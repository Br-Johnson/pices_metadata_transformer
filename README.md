# PICES FGDC to Zenodo Metadata Migration

This project transforms 4,206 FGDC XML metadata records to Zenodo JSON format and uploads them to the Zenodo sandbox for the PICES (North Pacific Marine Science Organization) metadata migration project.

## 🏗️ Project Structure

```
pices_md_2/
├── scripts/                    # All Python scripts
│   ├── orchestrate_pipeline.py # 🚀 Complete pipeline orchestration (RECOMMENDED)
│   ├── fgdc_to_zenodo.py      # Core transformation logic
│   ├── validate_zenodo.py     # Validation script
│   ├── pre_upload_duplicate_check.py # Pre-upload duplicate prevention
│   ├── batch_transform.py     # Batch transformation processor
│   ├── batch_upload.py        # Batched upload system with resume capability
│   ├── upload_audit.py        # Audit and verification system
│   ├── verify_uploads.py      # Post-upload verification
│   ├── deduplicate_check.py   # Duplicate detection and removal
│   ├── metrics_analysis.py    # Metrics analysis and reporting
│   ├── enhanced_metrics.py    # Enhanced metrics calculation
│   ├── record_review.py       # Individual record review tool
│   ├── publish_records.py     # Publish uploaded records
│   ├── generate_exclusion_lists.py # Generate exclusion lists
│   ├── zenodo_api.py          # Zenodo API client
│   └── logger.py              # Logging infrastructure
├── docs/                      # Documentation and reference files
│   ├── rfq.txt               # Request for Quote document
│   ├── fgdc_to_zenodo_crosswalk_exhaustive.csv # Field mappings
│   ├── tips_gotchas.txt      # Transformation tips and edge cases
│   ├── zenodo_api_docs.txt   # Zenodo API documentation
│   └── FDGC-STD-001-1998v2.txt # FGDC standard reference
├── FGDC/                     # Source FGDC XML files (4,206 files)
├── logs/                     # Log files and analysis reports
├── output/                   # Generated output files
├── transformed/              # Transformed JSON files and copies
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Production safety and review

The [exact42 resource reconciliation](docs/readiness/2026-10-03/resource_reconciliation_42_handoff.md)
adds reviewed finite contexts to the compatible556 profile, preserving all514
previous objects and unchanged821/904 evidence. Its measured delta and integrated
ledger yield **3638 supported /562 held /six malformed**. All raw metadata/XML and
456 alias/31 exception holds remain intact; new cases are REVIEWER_RECONCILED with
restricted unlicensed XML and separate provider gates.

The [exact22 forestry GIS cohort](docs/readiness/2026-10-03/cnf_copy_media_handoff.md)
adds finite copy-media acquisition interpretations while preserving literal
Unknown use, all raw metadata and original XML. Its measured22-source delta plus
the frozen full baseline yields **3490 source-supported /710 held /six malformed**;
this bounded comparison does not claim a fresh full-corpus or remote audit.
The [exact106 source integration](docs/readiness/2026-10-03/resource_scope_reconciliation_handoff.md)
adds23 source-backed resource contexts and83 reviewer-reconciled descriptions.
Its reproducible integrated ledger records **3596 source-supported /604 held /six
malformed**, using the frozen complete baseline and measured disjoint deltas.
All XML/raw metadata remain intact; [31 exact exceptions](docs/readiness/2026-10-03/pices-remaining31-exception-decisions.md)
remain held with source wording and specific questions.
The [remaining plain-language questions](docs/readiness/2026-10-03/pices-next-residual-questions.md)
retain the preceding156/60 inventory and existing
creator/date/title/alias holds.

The [bounded modern synthetic approval packet](docs/readiness/2026-10-03/modern_synthetic_approval_plan.md)
provides an isolated offline-tested Sandbox adapter, fixed fictional payload and
separate runtime/grant bindings. Parent dispatched the approved trial and reports
one durable POST intent with no retained response or established network dispatch.
All create allowances remain spent/held. The
[supported-route run02 handoff](docs/readiness/2026-10-03/modern_supported_route_handoff.md)
freezes a distinct fictional trial with the same action ceiling, preserving normal
environment routing and every old unresolved allowance. Its parent-bound dispatch
must fall within the existing user approval; code changes issue no live grant.
The [run02 body diagnostics](docs/readiness/2026-10-03/run02_body_diagnostics_handoff.md)
capture prepared JSON offline and freeze one canonical readback under the existing
recovery expiry. Both spent failed stages remain held; no repeated PUT or create.
The [fixed synthetic subjects correction](docs/readiness/2026-10-03/modern_subjects_correction_handoff.md)
projects the immutable fictional input to the modern subjects schema and retains
closed validation-error field flags before contract failure. All404 guarded tests
pass. Parent reports canonical GET197 still lacks all intended metadata; that
schema-correction handoff remains offline-only. Source counts remain3596/604/6;
the independently cleared next42 are identified only, awaiting separate integration.
The [same-draft controlled repair](docs/readiness/2026-10-03/run02_subjects_repair_handoff.md)
provides one explicitly bound corrected metadata PUT and one canonical GET within
a fresh ten-minute parent-dispatch window. All411 guarded tests pass; no new create,
old-state reset or root provider request. The grant and historical ledgers remain
separate, and successful repair verifies metadata only.
The
[exact821 source scope answer](docs/readiness/2026-10-03/source_scope_attestation.md)
supports791 promotions while retaining30 independent holds.
The [five retained-import preparation](docs/readiness/2026-10-03/five_import_correction_preparation.md)
binds five independently received full metadata beforeimages and source-derived
XML-artifact candidates, preserves existing DOIs/files, and identifies2043/2057's
1220 date holds. Saved file/version bindings are received and reconciled; a
modern revision baseline was not preserved. No live correction follows from
this preparation.

Use [reviewed correction batches](docs/curation_batches.md) for exact source-ID/hash
membership, overlap checks and explicit field precedence after common FGDC
transformations. The opt-in [Exxon citation profile](docs/readiness/2026-10-02/exxon_profile.md)
supports the audited mixed citation while preserving source attribution, rights,
alias holds and the separate production release gate.

Follow the [draft and evidence-bound QA runbook](docs/draft_qa_runbook.md) before using operational commands. Production stays draft until supported human or delegated agent record QA and separate explicit publication release. The [pinned review and offline reproductions](docs/reviews/2026-09-30/README.md) document the original defects.

The current [exact821 scope checkpoint](docs/readiness/2026-10-03/source_scope_attestation.md)
produces **3234 source-supported /966 held /six malformed**, with347 guarded
offline tests. All4194 complete metadata objects and every original XML are unchanged;
the user-attested clarification adds exact source-bound policy references only.
The preceding [13-source credit/title checkpoint](docs/readiness/2026-10-03/source_credit_title_13.md)
produces **2,443 source-supported /1,757 held / six malformed**, with 317 guarded
offline tests. It includes the preceding 142 batch and adds five literal credits and
eight bounded report titles, preserving full source context and every original XML.
Provider verification, exact existing ID/DOI ownership/file state and release remain
separate. [Three existing import identities](docs/readiness/2026-10-03/production_identity_adjudication.md)
are supported for corrections preserving their current DOIs; old byte provenance
is recorded as unknown and is not an identity-reuse blocker.

The preceding [finite source access checkpoint](docs/readiness/2026-10-03/finite_source_resource_access.md)
adds 142 exact source/hash/context interpretations from merged `4b13126`:
**2,430 source-supported / 1,770 held / six malformed**, with 312 guarded offline
tests. All 4,194 prepared metadata objects and every original XML remain unchanged;
source support still requires separate provider verification and release.
The [grouped decision packet](docs/readiness/2026-10-03/remaining_source_decision_packet.md)
froze821 sources under three wording questions now answered by Brett, and queued
13 smaller attribution/title proposals that are now implemented in the current checkpoint.

## 🚀 Quick Start

### 🎯 Recommended Approach: Use the Orchestration Pipeline

The **orchestrate_pipeline.py** script provides a complete, automated pipeline that handles all aspects of the migration:

```bash
# Run complete pipeline in sandbox (recommended for testing)
python3 scripts/orchestrate_pipeline.py --debug --limit 10

# Run complete pipeline in production
python3 scripts/orchestrate_pipeline.py --production --interactive

# Resume from previous run
python3 scripts/orchestrate_pipeline.py --resume
```

**Key Features:**

- ✅ **Complete automation** - Handles all steps from transformation to verification
- ✅ **Debug mode** - Test with minimal data and verbose output
- ✅ **Resume capability** - Continue from where you left off
- ✅ **Interactive mode** - Pause between steps for review
- ✅ **Comprehensive logging** - Full audit trail of all operations
- ✅ **Error recovery** - Graceful handling of failures
- ✅ **State management** - Tracks progress and prevents duplicate work

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd pices_md_2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your Zenodo API tokens
```

### 2. Run Complete Pipeline (Recommended)

The orchestration script runs the entire migration pipeline in logical order:

```bash
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
```

**Pipeline Steps:**

1. **Transform** FGDC XML files to Zenodo JSON (includes validation of newly transformed files)
2. **Pre-Upload Duplicate Check** - Check for existing records on Zenodo before upload
3. **Upload** to Zenodo (sandbox or production) - only safe-to-upload files
4. **Generate audit reports** and metrics
5. **Verify uploads** and data integrity
6. **Generate comprehensive reports**

## 🚫 Duplicate Prevention

### Pre-Upload Duplicate Check

The pipeline now includes a **pre-upload duplicate check** that prevents uploading records that already exist on Zenodo:

- **Checks existing records** on Zenodo before attempting upload
- **Identifies duplicates** by title similarity and DOI matching
- **Generates safe-to-upload list** containing only non-duplicate files
- **Saves API calls** by avoiding duplicate upload attempts
- **Prevents data pollution** in Zenodo repository

```bash
# Run pre-upload duplicate check manually
python scripts/pre_upload_duplicate_check.py --sandbox --limit 10

# The upload process automatically uses the safe-to-upload list
python scripts/batch_upload.py --sandbox
```

**Duplicate Detection Methods:**

- **Exact title match** - Identical titles (case-insensitive)
- **Similar title detection** - Fuzzy matching for similar titles
- **Comprehensive reporting** - Detailed duplicate analysis with existing record details

**Generated Files:**

- `safe_to_upload.json` - List of files safe to upload (no duplicates found)
- `already_uploaded_to_zenodo.json` - Complete list of existing records on Zenodo for filtering
- `pre_filter_already_uploaded.json` - Pre-filter list for transformation to skip already uploaded files
- `pre_upload_duplicate_check_*.json` - Detailed duplicate analysis report

**Pre-Filter Functionality:**
The duplicate check now generates a pre-filter list that can be used to skip transformation of files already uploaded to the PICES community. This prevents unnecessary processing and saves time:

```bash
# The batch transform automatically uses the pre-filter list
python scripts/batch_transform.py --input FGDC --output output --limit 100

# Files with titles matching already uploaded records will be skipped
# Check the transformation summary for "Skipped transformations" count
```

## 🐛 Debug Mode and Testing

### Debug Mode Features

The orchestration pipeline includes a comprehensive debug mode for testing and troubleshooting:

```bash
# Enable debug mode (automatically sets limit=5, interactive=True, verbose output)
python3 scripts/orchestrate_pipeline.py --debug

# Debug mode with dry run (see what would be executed)
python3 scripts/orchestrate_pipeline.py --debug --dry-run

# Debug specific steps
python3 scripts/orchestrate_pipeline.py --debug --skip-upload --skip-duplicates
```

**Debug Mode Automatically:**

- Sets limit to 5 files for testing
- Enables interactive mode
- Provides verbose output for all commands
- Shows detailed error information
- Validates all prerequisites
- Creates sample .env file if missing

### Testing Workflow

1. **Start with debug mode:**

   ```bash
   python3 scripts/orchestrate_pipeline.py --debug --dry-run
   ```

2. **Test with small dataset:**

   ```bash
   python3 scripts/orchestrate_pipeline.py --debug --limit 10
   ```

3. **Test individual steps:**

   ```bash
   python3 scripts/orchestrate_pipeline.py --debug --skip-upload --skip-duplicates
   ```

4. **Full test run:**
   ```bash
   python3 scripts/orchestrate_pipeline.py --debug
   ```

### 3. Individual Script Usage (Alternative)

If you prefer to run individual steps:

```bash
# Transform metadata
python scripts/batch_transform.py FGDC output --limit 10

# Upload to Zenodo
python scripts/batch_upload.py --sandbox --batch-size 100

# Check for duplicates
python scripts/deduplicate_check.py --sandbox

# Audit results
python scripts/upload_audit.py --output-dir output
```

## ⚠️ Common Issues and Solutions

### Date Field Warnings (Normal Behavior)

**Issue**: You may see warnings like:

```
WARNING - date_normalization: complex_date_range. Found: 72-88 thru 87-98
WARNING - date_normalization: date_range. Found: 1988 - Present
```

**Solution**: These are **NOT errors** - they're informational warnings. The system is correctly:

- Detecting complex FGDC date formats
- Converting them to valid ISO dates (e.g., "1972-01-01")
- Logging the conversion for transparency

**Action Required**: None. This is expected behavior.

### Function Signature Errors

**Issue**: Error like `transform_fgdc_file() takes 1 positional argument but 2 were given`

**Solution**: Always use the correct function signature:

```python
# ✅ Correct
result = transform_fgdc_file("path/to/file.xml")

# ❌ Incorrect
result = transform_fgdc_file("path/to/file.xml", "output/path")
```

### License Field Issues

**Issue**: Files rejected with invalid license "none"

**Solution**: Unknown source rights remain unresolved; the transformer does not default to CC0. Record a source-hash-bound rights decision supported by applicable permission/license evidence before an open deposit. Regenerating JSON does not establish a license. See the [artifact contract](docs/artifact_contract.md) and [curator decision matrix](docs/readiness/2026-10-01/curator_decision_matrix.md).

### Command Line Usage

**Issue**: Incorrect script arguments

**Solution**: Use the correct command format:

```bash
# ✅ Correct
python scripts/batch_transform.py --input FGDC --output output --limit 30

# ❌ Incorrect
python scripts/batch_transform.py --limit 30 --output-dir output
```

### Environment Setup

**Issue**: Missing API tokens

**Solution**: Ensure `.env` file exists with:

```
ZENODO_SANDBOX_TOKEN=your_sandbox_token_here
ZENODO_PRODUCTION_TOKEN=your_production_token_here
```

## 📋 Detailed Usage

### Orchestration Script

The `orchestrate_pipeline.py` script provides a comprehensive solution for running the entire migration pipeline with a single command. It handles all steps in logical order with proper error handling, progress tracking, and resume capability.

#### Command Options

```bash
python scripts/orchestrate_pipeline.py [options]

Environment Options:
  --sandbox          Use Zenodo sandbox (default: True)
  --production       Use Zenodo production (overrides --sandbox)

Mode Options:
  --interactive      Interactive mode: pause between major steps (default: False)
  --dry-run          Show what would be done without executing

Processing Options:
  --batch-size N     Upload batch size (default: 100)
  --limit N          Limit number of files to process (for testing)
  --output-dir DIR   Output directory (default: output)

Skip Options:
  --skip-transform   Skip transformation step (assume already done)
  --skip-upload      Skip upload step (assume already done)
  --skip-validation  Skip validation step
  --skip-duplicates  Skip duplicate checking
  --skip-audit       Skip audit and metrics generation

Resume Option:
  --resume           Resume from last successful step
```

#### Usage Examples

```bash
# Basic usage - run complete pipeline in sandbox
python scripts/orchestrate_pipeline.py

# Production run with interactive mode (recommended for production)
python scripts/orchestrate_pipeline.py --production --interactive

# Test run with limited files
python scripts/orchestrate_pipeline.py --limit 10 --interactive

# Resume interrupted pipeline
python scripts/orchestrate_pipeline.py --resume

# Skip transformation (if already done)
python scripts/orchestrate_pipeline.py --skip-transform

# Dry run to preview commands
python scripts/orchestrate_pipeline.py --dry-run

# Custom batch size and output directory
python scripts/orchestrate_pipeline.py --batch-size 50 --output-dir custom_output
```

#### Pipeline Steps

The orchestration script runs these steps in order:

1. **Prerequisites Check**

   - Verifies .env file exists
   - Checks FGDC directory
   - Ensures output directory is writable
   - Validates virtual environment

2. **Transform** (`--skip-transform` to skip)

   - Converts FGDC XML files to Zenodo JSON format
   - Handles all 4,206 files or limited subset
   - Generates transformation logs and metrics

3. **Validate** (`--skip-validation` to skip)

   - Validates transformed JSON files against Zenodo schema
   - Generates validation report
   - Identifies any transformation issues

4. **Upload** (`--skip-upload` to skip)

   - Uploads files to Zenodo (sandbox or production)
   - Uses configurable batch sizes
   - Handles rate limiting and error recovery
   - Supports interactive mode for review

5. **Check Duplicates** (`--skip-duplicates` to skip)

   - Scans for duplicate records
   - Compares local logs with Zenodo API
   - Generates duplicate detection report

6. **Audit** (`--skip-audit` to skip)

   - Generates comprehensive upload audit
   - Runs metrics analysis
   - Creates enhanced metrics report
   - Analyzes data quality and preservation

7. **Verify** (always runs)

   - Verifies uploads against Zenodo API
   - Checks data integrity
   - Validates record completeness

8. **Generate Reports** (always runs)
   - Creates comprehensive pipeline summary
   - Generates field analysis reports
   - Provides final statistics and recommendations

#### Interactive Mode

When `--interactive` is enabled, the script pauses between major steps:

```
⏸️  INTERACTIVE PAUSE: Upload files to Zenodo sandbox
   Step: upload
   Environment: sandbox
   Completed steps: transform, validate

   Continue? (y/n/s for skip):
```

- **y/yes**: Continue to next step
- **n/no**: Stop pipeline and exit
- **s/skip**: Skip current step and continue

#### Resume Capability

The script automatically saves progress to `output/pipeline_state_{environment}.json`. If interrupted:

```bash
# Resume from where it left off
python scripts/orchestrate_pipeline.py --resume
```

The script will:

- Load previous state
- Skip completed steps
- Continue from the last successful step
- Preserve all logs and reports

#### State Management

The orchestration script maintains detailed state information:

```json
{
  "start_time": "2025-01-11T12:00:00",
  "steps_completed": ["transform", "validate", "upload"],
  "current_step": "duplicates",
  "errors": [],
  "warnings": [],
  "config": {
    "environment": "sandbox",
    "interactive": true,
    "batch_size": 100
  }
}
```

#### Error Handling

The script provides robust error handling:

- **Command failures**: Logged and reported, pipeline can continue
- **Prerequisite failures**: Pipeline stops with clear error messages
- **User interruption**: State saved, can resume later
- **Unexpected errors**: Full error logging and graceful exit

#### Output Files

The orchestration script generates:

- `pipeline_state_{environment}.json` - Progress tracking
- `pipeline_summary_{environment}.json` - Final summary
- All standard output files from individual scripts
- Comprehensive logs and reports

### Transformation Process

The transformation process converts FGDC XML metadata to Zenodo JSON format following the comprehensive crosswalk mapping in `docs/fgdc_to_zenodo_crosswalk_exhaustive.csv`.

**Key Features:**

- Handles all 60+ FGDC elements
- Comprehensive edge case handling
- Detailed logging and error tracking
- Data integrity validation
- Character count analysis

**Command Options:**

```bash
python scripts/batch_transform.py --input FGDC --output output [options]

Options:
  --limit N        Process only N files (for testing)
  --input DIR      Input directory containing FGDC XML files (required)
  --output DIR     Output directory for transformed files (required)
  --verbose        Enable verbose logging
```

### Enhanced Field Mapping Analysis

Each transformed record includes comprehensive field mapping metrics to ensure **100% data preservation**:

```json
"field_mapping_breakdown": {
  "total_fgdc_fields": 62,
  "directly_mapped_fields": 12,
  "fields_in_notes": 50,
  "unmapped_fields": 0,
  "direct_mapping_percentage": 19.4,
  "notes_mapping_percentage": 80.6,
  "total_preservation_percentage": 100.0
}
```

**Key Metrics:**

- **Total FGDC Fields**: All fields found in the original FGDC XML
- **Directly Mapped**: Fields mapped directly to Zenodo schema (title, creators, description, keywords)
- **Fields in Notes**: Fields preserved in the notes field (purpose, constraints, contact info, etc.)
- **Unmapped Fields**: Fields not accounted for (should always be 0)
- **Total Preservation**: Percentage of FGDC fields preserved (should always be 100%)

**Analysis Commands:**

```bash
# Analyze field mapping across all transformed records
python scripts/metrics_analysis.py --output-dir output --save-report

# Generate enhanced metrics for specific files
python scripts/enhanced_metrics.py --input output/zenodo_json --output analysis.json
```

### Upload Process

The new batched upload system provides:

- **Rate limiting**: Stays within Zenodo limits (90 req/min, 4500 req/hour)
- **Resource management**: Proper cleanup with context managers
- **Error recovery**: Continues processing even if individual files fail
- **Progress tracking**: Can resume from any point
- **Audit trail**: Comprehensive logging and reporting
- **Duplicate prevention**: Centralized registry and API-based duplicate detection

**Command Options:**

```bash
python scripts/batch_upload.py [options]

Options:
  --sandbox        Use Zenodo sandbox (default: True)
  --production     Use Zenodo production (overrides --sandbox)
  --batch-size N   Number of files per batch (default: 1000)
  --limit N        Limit number of files to process (for testing)
  --interactive    Interactive mode: stop between batches for review (recommended for production)
  --output-dir DIR Output directory for logs (default: output)
```

### Interactive Mode (Recommended for Production)

For production uploads, use interactive mode to review each batch before proceeding:

```bash
# Production upload with interactive review
python scripts/batch_upload.py --production --interactive --batch-size 50

# Sandbox testing with interactive review
python scripts/batch_upload.py --sandbox --interactive --batch-size 10
```

Interactive mode provides:

- **Batch-by-batch review**: Stop after each batch to review results
- **Built-in tools**: Run duplicate checks and audits directly from the interface
- **Quality control**: Ensure each batch is successful before proceeding
- **Manual validation**: Review logs, reports, and individual records
- **Safe stopping**: Exit cleanly at any point with progress saved

### Duplicate Detection

The duplicate detection system provides:

- **Multi-source checking**: Compares local logs, centralized registry, and Zenodo API
- **Title-based detection**: Finds records with identical titles
- **Registry validation**: Ensures local tracking matches Zenodo state
- **Comprehensive reporting**: Detailed analysis of potential duplicates
- **Safe operation**: Report-only mode by default

### Audit and Verification

The audit system provides comprehensive reporting on:

- Upload success rates
- Error analysis and categorization
- Data integrity checks
- Performance metrics
- Recommendations for improvements

**Command Options:**

```bash
python scripts/upload_audit.py [options]

Options:
  --output-dir DIR Directory containing upload logs
  --report-file FILE Save human-readable report to file
```

**Duplicate Detection Options:**

```bash
python scripts/deduplicate_check.py [options]

Options:
  --sandbox        Check sandbox Zenodo (default: True)
  --production     Check production Zenodo (overrides --sandbox)
  --output-dir DIR Output directory for reports (default: output)
  --check-files    Comma-separated list of specific files to check
  --report-only    Generate report only, do not delete duplicates (default: True)
```

## 🔧 Configuration

### Environment Variables

Token precedence is an explicit `create_zenodo_client(access_token=...)` argument,
then the selected nonempty `ZENODO_SANDBOX_TOKEN` or `ZENODO_PRODUCTION_TOKEN`
environment variable, then the legacy `.env` file in the current working directory.
An empty environment variable falls back to `.env`; sandbox and production never
fall back to each other's token. Environment values are opaque and passed unchanged
into session and bucket `Authorization: Bearer` headers, including NetworkSecret
placeholders. The loader does not resolve placeholders or log token values.
Tokens must be nonempty printable ASCII without whitespace: invalid environment,
file, or explicit tokens fail closed before creating a session. Valid placeholders
pass unchanged. Empty environment variables retain the file fallback described
above; empty explicit/file tokens are rejected. Transport errors omit exception
text and chained tracebacks; remote error diagnostics report HTTP status only.
Legacy `.env` parsing still trims surrounding whitespace without unquoting values.
Credential provisioning requires separate secure approval; this compatibility
change does not provision credentials or authorize uploads.

For the legacy file option, create a `.env` file with your Zenodo API tokens:

```bash
ZENODO_SANDBOX_TOKEN=your_sandbox_token_here
ZENODO_PRODUCTION_TOKEN=your_production_token_here
```

### Rate Limiting

The system automatically handles Zenodo's rate limits:

- **Minute limit**: 90 requests/minute (safely under 100/min limit)
- **Hour limit**: 4500 requests/hour (safely under 5000/hour limit)
- **Request interval**: 0.7 seconds between requests

### Batch Sizes

Recommended batch sizes:

- **Testing**: 5-10 files
- **Development**: 100 files
- **Production**: 1000 files

## 📊 Monitoring and Logging

### Log Files

The system generates comprehensive logs:

- `logs/transform_*.log` - Transformation progress and issues
- `logs/warnings.json` - Structured warnings with context
- `logs/errors.json` - Errors requiring attention
- `logs/progress.csv` - Cumulative progress tracking
- `output/batch_upload_log_*.json` - Upload progress and results
- `output/upload_audit_*.json` - Comprehensive audit data

### Progress Tracking

Monitor progress with:

```bash
# Check transformation progress
tail -f logs/transform_*.log

# Check upload progress
tail -f output/batch_upload_log_*.json

# Generate audit report
python scripts/upload_audit.py
```

## 🔍 Record Review and Analysis

### Individual Record Review

Use the comprehensive record review helper to analyze specific transformations:

```bash
# Review a specific record
python scripts/record_review.py FGDC-1234

# Review with Zenodo verification
python scripts/record_review.py FGDC-1234 --check-zenodo

# Review in production environment
python scripts/record_review.py FGDC-1234 --production
```

### Review Output

The record review provides:

- **Overall Status**: Excellent/Good/Fair/Poor with quality score
- **File Status**: Which files exist (original FGDC, transformed JSON)
- **Original FGDC Analysis**: File size, XML structure, key field presence
- **Transformed JSON Analysis**: Field coverage, data preservation ratios
- **Upload Analysis**: Upload status, deposition ID, DOI, timestamp
- **Issue Analysis**: Warnings, errors, validation issues
- **Zenodo Verification**: Live check against Zenodo API (optional)

### Enhanced Metrics

The system now provides comprehensive metrics:

#### Data Preservation Metrics

- **Content Preservation Ratio**: Percentage of meaningful content preserved
- **Field Preservation Ratio**: Percentage of FGDC fields successfully mapped
- **Semantic Preservation Score**: Quality of meaning preservation
- **Data Loss/Gain Indicators**: Specific issues identified

#### Field Coverage Analysis

- **Critical Fields**: Title, creators, publication date, description (weighted 70%)
- **Important Fields**: Keywords, license, access rights, communities (weighted 20%)
- **Optional Fields**: Notes, references, contributors (weighted 10%)
- **Weighted Coverage Score**: Overall field completeness

#### Data Quality Assessment

- **Title Quality**: Length, formatting, capitalization
- **Creator Quality**: Name format, completeness
- **Description Quality**: Length, sentence structure
- **Keyword Quality**: Count, length, relevance
- **Date Quality**: Format validation, reasonableness
- **License Quality**: Valid license identification

#### Transformation Effectiveness

- **Mapping Completeness**: How well FGDC fields were mapped
- **Data Enrichment**: Additional value added during transformation
- **Format Compliance**: Zenodo schema compliance
- **Semantic Accuracy**: Meaning preservation quality

#### Compliance Metrics

- **Zenodo Required Fields**: 100% required for upload
- **Zenodo Recommended Fields**: Best practices compliance
- **PICES Community**: Community membership verification
- **Open Access**: Access rights compliance
- **License Compliance**: Valid license usage

### Quality Scoring

Records are scored on a 0-100 scale with letter grades:

- **A (90-100)**: Excellent quality, all requirements met
- **B (80-89)**: Good quality, minor issues
- **C (70-79)**: Fair quality, some concerns
- **D (60-69)**: Poor quality, significant issues
- **F (0-59)**: Failed quality, major problems

### Example Review Output

```
🟢 OVERALL STATUS: EXCELLENT
📊 Data Quality Score: 95.0%
🔄 Transformation: ✅
⬆️  Upload: ✅

📁 FILES:
   Original FGDC: ✅
   Transformed JSON: ✅

📄 ORIGINAL FGDC ANALYSIS:
   File size: 4.39 KB
   XML elements: 90
   Title: ✅
   Creators: ✅
   Abstract: ✅
   Keywords: ✅
   Spatial bounds: ✅

🔄 TRANSFORMED JSON ANALYSIS:
   Fields present: 13/13
   Required fields: 4/4
   Data preservation: 95.2%
   Quality grade: A

⬆️  UPLOAD ANALYSIS:
   Status: success
   Deposition ID: 348189
   DOI: 10.5281/zenodo.348189
```

### Bulk Metrics Analysis

Analyze enhanced metrics across all transformed records:

```bash
# Analyze all records and print summary
python scripts/metrics_analysis.py

# Analyze and save detailed report
python scripts/metrics_analysis.py --save-report

# Analyze with custom output directory
python scripts/metrics_analysis.py --output-dir custom_output --save-report
```

The metrics analysis provides:

- **Overall Score Distribution**: Average, median, min/max scores across all records
- **Quality Grade Distribution**: Count and percentage of A/B/C/D/F grades
- **Field Coverage Analysis**: Average coverage for critical/important/optional fields
- **Compliance Analysis**: Zenodo compliance rates and PICES community membership
- **Transformation Effectiveness**: Mapping completeness and data enrichment scores
- **Actionable Recommendations**: Specific improvements based on analysis patterns

### Metrics Assessment

#### Character Count Analysis

Focuses on **meaningful content preservation**:

- Extracts only text content from key FGDC elements
- Calculates semantic preservation scores
- Identifies specific data loss/gain patterns
- Provides actionable insights for transformation improvements

#### Field Coverage Analysis

- **Critical fields** (70% weight): title, creators, publication_date, description
- **Important fields** (20% weight): keywords, license, access_right, communities
- **Optional fields** (10% weight): notes, references, contributors
- **Weighted coverage score** provides meaningful completeness metric

#### Data Integrity Metrics

- **Quality grades** (A-F) with clear thresholds (90+, 80+, 70+, 60+, <60)
- **Percentage-based scoring** for all coverage metrics
- **Clear definitions** for each metric category
- **Actionable recommendations** based on analysis patterns

## 🛠️ Troubleshooting

### Common Issues

1. **Rate Limiting Errors**

   - The system automatically handles rate limits
   - If you see rate limit errors, the system will wait and retry

2. **Resource Leaks**

   - The new system uses context managers for proper cleanup
   - If you see semaphore warnings, restart the process

3. **Upload Failures**

   - Check the audit report for error patterns
   - Use smaller batch sizes for problematic files
   - The system can resume from where it left off

4. **Memory Issues**

   - Use smaller batch sizes
   - The system processes files one at a time to minimize memory usage

5. **Duplicate Records**

   - Run duplicate check: `python scripts/deduplicate_check.py --sandbox`
   - Review the report for title duplicates and registry mismatches
   - Use `--check-files` to verify specific files
   - The system now prevents duplicates automatically during upload

6. **Pipeline Interruption**
   - Use the orchestration script with `--resume` to continue from where it left off
   - Check `output/pipeline_state_{environment}.json` for progress
   - Individual scripts can be run separately if needed

### Recovery

If an upload is interrupted:

```bash
# The system automatically resumes from where it left off
python scripts/batch_upload.py --sandbox --batch-size 100
```

## 🔄 Recent Improvements

### Pipeline Orchestration

- ✅ **Complete automation** - Single command runs entire migration
- ✅ **Debug mode** - Comprehensive testing and troubleshooting
- ✅ **Resume capability** - Continue from interruptions
- ✅ **State management** - Tracks progress and prevents duplicate work
- ✅ **Error recovery** - Graceful handling of failures

### Code Cleanup

- ✅ **Removed redundant scripts** - Consolidated functionality
- ✅ **Standardized interfaces** - Consistent command-line arguments
- ✅ **Enhanced logging** - Comprehensive audit trails
- ✅ **Improved error handling** - Better error messages and recovery

### Quality Assurance

- ✅ **Comprehensive validation** - Multi-layer validation system
- ✅ **Duplicate detection** - Prevents duplicate uploads
- ✅ **Audit reporting** - Detailed analysis and metrics
- ✅ **Verification system** - Post-upload validation

## 📈 Performance Metrics

### Expected Performance

- **Transformation**: ~0.1 seconds per file
- **Upload**: ~3-4 seconds per file (including rate limiting)
- **Total time**: ~2-3 hours for all 4,206 files

### Success Rates

- **Transformation**: >99% success rate
- **Upload**: >95% success rate
- **Data integrity**: >98% pass validation

## 🔍 Quality Assurance

### Validation

All transformed records are validated against:

- Zenodo schema requirements
- Required field presence
- Data format validation
- URL validation
- Date format validation

### Data Integrity

The system tracks:

- Character count preservation
- Field coverage analysis
- Missing data identification
- Transformation accuracy

## 📚 Documentation

- `docs/rfq.txt` - Project requirements and scope
- `docs/fgdc_to_zenodo_crosswalk_exhaustive.csv` - Complete field mappings
- `docs/tips_gotchas.txt` - Edge cases and transformation tips
- `docs/zenodo_api_docs.txt` - Zenodo API reference

## 🤝 Contributing

1. Follow the existing code structure
2. Add comprehensive logging for any new features
3. Update documentation for any changes
4. Test with small batches before full runs
5. Ensure proper error handling and resource cleanup

## 📄 License

This project is part of the PICES metadata migration initiative.

## 🆘 Support

For issues or questions:

1. Check the logs for detailed error information
2. Review the audit reports for patterns
3. Use the test scripts to isolate issues
4. Consult the documentation in the `docs/` directory

Original FGDC XML attachments are available through the explicitly reviewed [artifact contract](docs/artifact_contract.md). Legacy records are not automatically reclassified. The [three-candidate decision packet](docs/readiness/2026-10-02/candidate_decisions.md) separates remaining source-policy decisions from completed offline engineering.

Offline source classification can apply the exact, source-bound [Contact Source access interpretation](docs/readiness/2026-10-02/contact_source_cohort.md) alongside existing restoration authority. The documented optional flag preserves dataset restrictions, restricted XML, blank licenses and separate live QA/release gates.

The separate [Contributor or Source interpretation](docs/readiness/2026-10-02/contributor_source_profile.md) records Brett's 23:43 UTC attestation for exactly 585 source/hash pairs. Enable it with `--contributor-access-interpretation-manifest`; it does not remove independent creator/date holds or grant a license or publication approval.

A narrow [sandbox canary handoff](docs/handoff/sandbox-canary-20261002/EXECUTOR.md) supports previously authorized historical duplicate tolerance for exactly three pinned sources. It requires the explicit `canary_plan` checker/service argument and a dedicated namespace-bound sandbox ledger; there is no global duplicate override. Production rejects the exception. The frozen plan, inventory freshness, own-run idempotency and draft-only gates remain mandatory.

The opt-in [literal institutional citation profile](docs/readiness/2026-10-03/institution_citation_profile.md) pins 72 source/hash pairs while preserving full creator objects and all metadata. Together with the reviewed DFO70 profile, fresh/resumed source-only QA supports 2,121 records; nine new-cohort residuals, remote verification and production release gates remain held.

The additive [institution/program citation extension](docs/readiness/2026-10-03/institution_program_citation_99.md) uses the same opt-in option and preserves the previous 72 cohort objects plus 27 exact new source bindings. Fresh/resumed source-only QA now supports 2,137 records, with eleven new-cohort access holds retained. Complete metadata objects and original/copied XML bytes remain unchanged; [parallel residual role/access reviews](docs/readiness/2026-10-03/residual_role_access_review.md) and [uncertain Sandbox-create recovery](docs/readiness/2026-10-03/uncertain_create_recovery_recommendation.md) remain separate from live QA and release.

The [reviewed joint/collection citation profile](docs/readiness/2026-10-03/joint_collection_citation_190.md) retains those 99 cohort objects and adds 91 exact bindings. It corrects 68 joint creator lists with bounded citation notes, retains Unaami's literal collection attribution, and yields 2,138 source-supported records with 90 cohort access holds. Original/copied XML, all other metadata fields, dates and rights remain unchanged. Complete offline duplicate/source-integrity preparation protects historical existing record IDs/DOIs without claiming current remote identity or release approval.

The [read-only alias reconciliation](docs/readiness/2026-10-03/source_alias_reconciliation.md) maps all 456 held identities to 228 neutral XML-byte groups, retaining every source/payload/submission hash and leaving provider canonical IDs/DOIs unset. Identical prepared metadata still produces distinct source-bound submission fingerprints. It also records 39 next literal-citation candidates and a [morning meaning bundle](docs/readiness/2026-10-03/morning_source_decisions.md) for the 90 access holds. This analysis installs no source interpretation or eligibility change.

The subsequent [229-member literal-citation extension](docs/readiness/2026-10-03/literal_citation_extension_229.md) supports those 39 exact sources after full-object review and actual offline validation: 2,177 supported / 2,023 held / six malformed. All 4,194 complete metadata objects and source/copy bytes remain unchanged; only bounded creator-policy references change. All access and alias holds, unsupported creator/date cases, provider verification and production release gates remain intact.

The [reviewed source-credit and historical-link checkpoint](docs/readiness/2026-10-03/source_credit_and_linkage.md) adds 90 exact citation interpretations and 21 dataset link preservation corrections. Actual guarded validation yields **2,288 supported / 1,912 held / six malformed**, exactly 111 promotions, with 301 tests independently reproduced. All 4,206 original hashes and 4,200 XML copies are preserved; 4,083 complete prepared metadata objects remain unchanged. Source support remains separate from provider verification and release. The 319-member creator profile preserves every earlier 229 cohort object; all 456 aliases, 90 joint/collection access holds and uncertain canary state remain held. Further source-only cleanup candidates among 86 access-held records are ranked without claiming approved after-images or access promotion.

The [access-held source-credit cleanup](docs/readiness/2026-10-03/access_held_source_credits.md) completes the exact 86-record review: 77 bounded citation corrections, including all five literal siblings, while nine attribution gaps and all 86 access holds remain. Source counts stay **2,288 supported / 1,912 held / six malformed**. The 396-member opt-in profile preserves all 143 earlier cohort objects covering 319 source bindings; 34 creator lists change and 43 remain intact with reviewed source notes. All original bytes, dates, rights, aliases, earlier access decisions and uncertain canary state are preserved; 306 guarded contracts pass.
